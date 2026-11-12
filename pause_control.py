"""Global pause and resume control for the desktop agent.

The agent registers ``Alt+F10`` as a Windows system-wide hotkey, so the same
shortcut works whether the GUI is focused, minimized, or the agent was started
from a terminal. Pressing it toggles a pause flag. The agent loop checks that
flag before taking another action and waits until the flag is cleared.

The GUI can also send ``toggle`` through the child process's standard input.
That path is enabled with ``GEMINI_PC_USE_STDIN_CONTROL=1`` so normal
command-line runs never consume terminal input.
"""

from __future__ import annotations

import ctypes
import logging
import os
import sys
import threading
import time
from ctypes import wintypes

logger = logging.getLogger("computer-use")

HOTKEY_NAME = "Alt+F10"
MOD_ALT = 0x0001
MOD_NOREPEAT = 0x4000
VK_F10 = 0x79
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
_HOTKEY_ID = 0x4743  # Arbitrary application id ("GC").


class PauseController:
    """Thread-safe pause flag plus a Windows global-hotkey listener."""

    def __init__(self) -> None:
        self._running = threading.Event()
        self._running.set()
        self._stopped = threading.Event()
        self._state_lock = threading.Lock()
        self._paused = False
        self._hotkey_thread: threading.Thread | None = None
        self._hotkey_thread_id: int | None = None
        self._stdin_thread: threading.Thread | None = None
        self._started = False

    @property
    def paused(self) -> bool:
        """Return the current pause state."""
        with self._state_lock:
            return self._paused

    def start(self) -> None:
        """Start the global hotkey listener and optional stdin control."""
        if self._started:
            return
        self._started = True
        self._start_hotkey()
        self._start_stdin_control()

    def stop(self) -> None:
        """Unregister the hotkey and release any paused waiter."""
        self._stopped.set()
        self._running.set()
        thread_id = self._hotkey_thread_id
        if sys.platform == "win32" and thread_id:
            try:
                ctypes.windll.user32.PostThreadMessageW(thread_id, WM_QUIT, 0, 0)
            except (AttributeError, OSError):
                pass
        if self._hotkey_thread is not None:
            self._hotkey_thread.join(timeout=1.5)
            self._hotkey_thread = None

    def toggle(self) -> None:
        """Pause a running agent, or resume a paused one."""
        with self._state_lock:
            paused = not self._paused
            self._paused = paused
        if paused:
            self._running.clear()
            logger.warning(
                "[PAUSED] Agent paused. Press %s to resume.", HOTKEY_NAME
            )
        else:
            self._running.set()
            logger.info("[RESUMED] Agent resumed. Continuing the task.")

    def pause(self) -> None:
        """Pause the agent if it is currently running."""
        with self._state_lock:
            if self._paused:
                return
            self._paused = True
        self._running.clear()
        logger.warning("[PAUSED] Agent paused. Press %s to resume.", HOTKEY_NAME)

    def resume(self) -> None:
        """Resume the agent if it is currently paused."""
        with self._state_lock:
            if not self._paused:
                return
            self._paused = False
        self._running.set()
        logger.info("[RESUMED] Agent resumed. Continuing the task.")

    def wait_if_paused(self, cancel_event: threading.Event | None = None) -> None:
        """Block while paused, checking periodically so shutdown stays quick."""
        while not self._running.is_set() and not self._stopped.is_set():
            if cancel_event is not None and cancel_event.is_set():
                return
            self._running.wait(0.1)

    def sleep(
        self,
        seconds: float,
        cancel_event: threading.Event | None = None,
    ) -> None:
        """Sleep for *seconds* while staying responsive to pause and stop."""
        deadline = time.monotonic() + max(0.0, seconds)
        while not self._stopped.is_set():
            self.wait_if_paused(cancel_event)
            if cancel_event is not None and cancel_event.is_set():
                return
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            time.sleep(min(0.1, remaining))

    # --------------------------------------------------------------- hotkey
    def _start_hotkey(self) -> None:
        if sys.platform != "win32":
            logger.info(
                "Global pause hotkey %s is only available on Windows.",
                HOTKEY_NAME,
            )
            return
        self._hotkey_thread = threading.Thread(
            target=self._hotkey_loop,
            name="pause-hotkey",
            daemon=True,
        )
        self._hotkey_thread.start()

    def _hotkey_loop(self) -> None:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        self._hotkey_thread_id = int(kernel32.GetCurrentThreadId())

        register = user32.RegisterHotKey
        register.argtypes = [
            wintypes.HWND,
            ctypes.c_int,
            wintypes.UINT,
            wintypes.UINT,
        ]
        register.restype = wintypes.BOOL
        if not register(None, _HOTKEY_ID, MOD_ALT | MOD_NOREPEAT, VK_F10):
            logger.warning(
                "Could not register %s. Another program may already use it. "
                "Use the Pause button in the GUI instead.",
                HOTKEY_NAME,
            )
            return

        logger.info(
            "Global pause hotkey ready: %s pauses or resumes the agent "
            "anywhere in Windows.",
            HOTKEY_NAME,
        )
        try:
            message = wintypes.MSG()
            get_message = user32.GetMessageW
            get_message.argtypes = [
                ctypes.POINTER(wintypes.MSG),
                wintypes.HWND,
                wintypes.UINT,
                wintypes.UINT,
            ]
            get_message.restype = ctypes.c_int
            while not self._stopped.is_set():
                result = get_message(ctypes.byref(message), None, 0, 0)
                if result <= 0:
                    break
                if message.message == WM_HOTKEY and int(message.wParam) == _HOTKEY_ID:
                    self.toggle()
        finally:
            user32.UnregisterHotKey(None, _HOTKEY_ID)

    # ---------------------------------------------------------------- stdin
    def _start_stdin_control(self) -> None:
        if os.environ.get("GEMINI_PC_USE_STDIN_CONTROL") != "1":
            return
        if sys.stdin is None:
            return
        self._stdin_thread = threading.Thread(
            target=self._stdin_loop,
            name="pause-stdin",
            daemon=True,
        )
        self._stdin_thread.start()

    def _stdin_loop(self) -> None:
        try:
            for line in sys.stdin:
                command = line.strip().lower()
                if command == "toggle":
                    self.toggle()
                elif command == "pause":
                    self.pause()
                elif command == "resume":
                    self.resume()
                elif command in {"quit", "stop"}:
                    return
        except (OSError, ValueError):
            return
