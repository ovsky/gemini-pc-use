"""Desktop automation primitives backed by PyAutoGUI."""

from __future__ import annotations

import logging

import pyautogui

logger = logging.getLogger(__name__)


class DesktopComputer:
    """Thin, fast wrapper around PyAutoGUI used by the agent.

    Parameters
    ----------
    instant_click:
        When True the pointer is placed on the target and clicked in one step,
        with no travel animation. This is noticeably faster and is the
        recommended mode once the model is working reliably.
    move_duration:
        Duration of the pointer animation in normal mode, in seconds.
    """

    def __init__(
        self,
        *,
        instant_click: bool = False,
        move_duration: float = 0.18,
        type_interval: float = 0.015,
        failsafe: bool = False,
    ) -> None:
        self.instant_click = instant_click
        self.move_duration = 0.0 if instant_click else max(0.0, move_duration)
        self.type_interval = max(0.0, type_interval)
        self.done = False
        pyautogui.FAILSAFE = failsafe
        # The default 0.1 s pause after every call adds up over a long run.
        pyautogui.PAUSE = 0.03

    @staticmethod
    def screen_size() -> tuple[int, int]:
        return pyautogui.size()

    @staticmethod
    def _to_pixels(x: int | float, y: int | float) -> tuple[int, int]:
        width, height = pyautogui.size()
        pixel_x = int((float(x) / 1000.0) * width)
        pixel_y = int((float(y) / 1000.0) * height)
        return pixel_x, pixel_y

    def _move(self, pixel_x: int, pixel_y: int) -> None:
        if self.instant_click:
            return
        pyautogui.moveTo(
            pixel_x,
            pixel_y,
            duration=self.move_duration,
            tween=pyautogui.easeOutQuad,
        )

    def move_mouse(self, x: int, y: int) -> None:
        """Move the pointer to a normalized coordinate without clicking."""
        pixel_x, pixel_y = self._to_pixels(x, y)
        logger.info("Moving pointer to (%d, %d)", pixel_x, pixel_y)
        self._move(pixel_x, pixel_y)

    def click_at(self, x: int, y: int) -> None:
        """Click once at a normalized coordinate (0-1000)."""
        pixel_x, pixel_y = self._to_pixels(x, y)
        logger.info("Clicking at (%d, %d)", pixel_x, pixel_y)
        if self.instant_click:
            pyautogui.click(pixel_x, pixel_y)
        else:
            self._move(pixel_x, pixel_y)
            pyautogui.click()

    def double_click_at(self, x: int, y: int) -> None:
        """Double-click at a normalized coordinate (0-1000)."""
        pixel_x, pixel_y = self._to_pixels(x, y)
        logger.info("Double-clicking at (%d, %d)", pixel_x, pixel_y)
        if self.instant_click:
            pyautogui.doubleClick(pixel_x, pixel_y)
        else:
            self._move(pixel_x, pixel_y)
            pyautogui.doubleClick()

    def type_text_at(
        self,
        x: int,
        y: int,
        text: str,
        press_enter: bool = False,
    ) -> None:
        """Click at a normalized coordinate, type text, and optionally press Enter."""
        pixel_x, pixel_y = self._to_pixels(x, y)
        logger.info("Typing %d characters at (%d, %d)", len(text), pixel_x, pixel_y)
        if self.instant_click:
            pyautogui.click(pixel_x, pixel_y)
        else:
            self._move(pixel_x, pixel_y)
            pyautogui.click()
        self.type_text(text, press_enter=press_enter)

    def type_text(self, text: str, press_enter: bool = False) -> None:
        """Type text into the currently focused control."""
        if text:
            pyautogui.write(text, interval=self.type_interval)
        if press_enter:
            pyautogui.press("enter")

    def press_key(self, key: str) -> None:
        """Press a single key, for example Enter, Tab, Escape, or Win."""
        logger.info("Pressing key %s", key)
        pyautogui.press(key)

    def hotkey(self, keys: list[str]) -> None:
        """Press a key combination such as Ctrl+S or Win+R."""
        logger.info("Pressing hotkey %s", " + ".join(keys))
        pyautogui.hotkey(*keys)

    def mark_done(self) -> None:
        """Mark the task as finished."""
        self.done = True
