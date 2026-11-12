"""Gemini-powered desktop agent.

The agent repeatedly:
1. takes a screenshot,
2. asks Gemini for the next single tool call,
3. executes that call with PyAutoGUI,
4. logs a human-readable explanation of what it did and why.

Everything is written in English and is designed to be fast: screenshots are
downscaled and encoded once, the Gemini client is reused for the whole run, the
old fixed two-second sleeps are gone, and instant click mode can skip pointer
travel entirely.
"""

from __future__ import annotations

import io
import json
import logging
import platform
import sys
import threading
import time
from typing import Any

import google.genai as genai
import pyautogui
from google.genai import types

from action_guide import describe_action
from computer import DesktopComputer
from config import (
    DEFAULT_MAX_STEPS,
    DEFAULT_MODEL,
    DEFAULT_STEP_DELAY,
    load_config,
    load_env_file,
    resolve_api_key,
)
from pause_control import PauseController

logger = logging.getLogger(__name__)

FALLBACK_MODELS = ("gemini-3.5-flash", DEFAULT_MODEL)
MAX_CONSECUTIVE_ERRORS = 4
MAX_EMPTY_RESPONSES = 4
HISTORY_LIMIT = 12
IMAGE_MAX_WIDTH = 1280
IMAGE_MAX_HEIGHT = 720
JPEG_QUALITY = 78


def _system_prompt() -> str:
    os_name = platform.system() or "Windows"
    if os_name == "Windows":
        desktop = "Windows 11"
    elif os_name == "Darwin":
        desktop = "macOS"
    else:
        desktop = "Linux"

    return f"""
You control a {desktop} desktop. Your job is to reach the user's goal by calling
the provided tools, one action at a time.

Important rules:
- Coordinates (x, y) are normalized from 0 to 1000. (0, 0) is the top-left
  corner and (1000, 1000) is the bottom-right corner.
- To open a desktop icon, folder, file, or program, you MUST use
  `double_click_at`.
- To press a button or select an item, use `click_at`.
- To launch programs quickly, use `hotkey` with ['Win', 'r'], then type the
  program name.
- When you need to enter text, use `type_text_at` (or `type_text` when the
  input already has focus).
- Confirm dialogs and submissions with `press_key` and the 'enter' key.
- Some buttons, especially 'Next' or 'Continue', may look disabled or greyed
  out even though they are clickable. If 'Next' is the logical next step, try
  clicking it.
- Prefer keyboard shortcuts over mouse clicks when they are clearly faster.
- Never repeat an action that just failed in the same way. Inspect the new
  screenshot and try a different approach.
- When the task is fully complete, call `done`.
""".strip()


# Tool definitions. The docstrings become the tool descriptions that Gemini
# reads, which makes them part of the prompt. Keep them short and precise.
def click_at(x: int, y: int) -> None:
    """Click once with the left mouse button at normalized coordinates (0-1000)."""


def double_click_at(x: int, y: int) -> None:
    """Double-click with the left mouse button at normalized coordinates (0-1000)."""


def type_text_at(x: int, y: int, text: str, press_enter: bool = False) -> None:
    """Click at (x, y) (0-1000), type text, and optionally press Enter."""


def type_text(text: str, press_enter: bool = False) -> None:
    """Type text into the currently focused control and optionally press Enter."""


def press_key(key: str) -> None:
    """Press a single key, for example 'enter', 'tab', 'esc', or 'win'."""


def hotkey(keys: list[str]) -> None:
    """Press a key combination together, for example ['Win', 'r'] or ['ctrl', 's']."""


def done() -> None:
    """Call this when the user's goal has been fully achieved."""


TOOLS = [click_at, double_click_at, type_text_at, type_text, press_key, hotkey, done]

KEY_ALIASES = {
    "win": "win",
    "windows": "win",
    "super": "win",
    "meta": "win",
    "cmd": "win",
    "command": "win",
    "control": "ctrl",
    "ctrl": "ctrl",
    "alt": "alt",
    "shift": "shift",
    "enter": "enter",
    "return": "enter",
    "escape": "esc",
    "esc": "esc",
    "backspace": "backspace",
    "delete": "delete",
    "del": "delete",
    "tab": "tab",
    "space": "space",
    "pageup": "pageup",
    "page_down": "pagedown",
    "pagedown": "pagedown",
    "page_up": "pageup",
    "up": "up",
    "down": "down",
    "left": "left",
    "right": "right",
    "home": "home",
    "end": "end",
}


def normalize_key(key: str) -> str:
    """Map common key names to the names PyAutoGUI expects."""
    normalized = key.strip()
    return KEY_ALIASES.get(normalized.lower(), normalized.lower())


def _model_candidates(primary: str) -> list[str]:
    candidates: list[str] = []
    for name in (primary, *FALLBACK_MODELS):
        if name and name not in candidates:
            candidates.append(name)
    return candidates


def _encode_screenshot(screenshot: Any) -> bytes:
    """Downscale and JPEG-encode a screenshot, preserving aspect ratio."""
    image = screenshot.copy()
    image.thumbnail((IMAGE_MAX_WIDTH, IMAGE_MAX_HEIGHT))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=JPEG_QUALITY, optimize=False)
    return buffer.getvalue()


def _format_history(history: list[str]) -> str:
    if not history:
        return "This is the first step."
    recent = history[-HISTORY_LIMIT:]
    return "Previous actions:\n" + "\n".join(recent)


def _is_retryable(error: Exception) -> bool:
    text = str(error).lower()
    markers = (
        "429",
        "500",
        "502",
        "503",
        "504",
        "deadline",
        "timeout",
        "temporarily unavailable",
        "unavailable",
        "overloaded",
        "rate limit",
        "connection reset",
    )
    return any(marker in text for marker in markers)


def run_agent(
    user_prompt: str,
    *,
    api_key: str | None = None,
    model: str | None = None,
    instant_click: bool | None = None,
    max_steps: int | None = None,
    step_delay: float | None = None,
    save_screenshots: bool | None = None,
    cancel_event: threading.Event | None = None,
    pause_controller: PauseController | None = None,
) -> bool:
    """Run the agent until it finishes, fails, or reaches the step limit.

    Returns True when the model reports success.
    """
    load_env_file()
    config = load_config()

    resolved_key = (api_key or resolve_api_key(config)).strip()
    if not resolved_key:
        logger.error(
            "GEMINI_API_KEY was not found. Save it in the GUI or with "
            "`py -3.13 main.py --save-key`, or set it in your environment."
        )
        return False

    model_name = (model or config.get("model") or DEFAULT_MODEL).strip()
    models_to_try = _model_candidates(model_name)
    model_index = 0
    model_name = models_to_try[model_index]

    if instant_click is None:
        instant_click = bool(config.get("instant_click", False))
    if max_steps is None:
        max_steps = int(config.get("max_steps", DEFAULT_MAX_STEPS))
    if step_delay is None:
        step_delay = float(config.get("step_delay", DEFAULT_STEP_DELAY))
    if save_screenshots is None:
        save_screenshots = bool(config.get("save_screenshots", False))

    controller = pause_controller or PauseController()

    client = genai.Client(api_key=resolved_key)
    generate_config = types.GenerateContentConfig(
        temperature=0.1,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        tools=TOOLS,
    )

    computer = DesktopComputer(instant_click=instant_click)
    screen_width, screen_height = computer.screen_size()
    logger.info(
        "Agent starting | model=%s | screen=%dx%d | instant_click=%s | max_steps=%d",
        model_name,
        screen_width,
        screen_height,
        instant_click,
        max_steps,
    )
    logger.info("Goal: %s", user_prompt)

    history: list[str] = []
    consecutive_errors = 0
    empty_responses = 0

    for step in range(1, max_steps + 1):
        controller.wait_if_paused(cancel_event)
        if cancel_event is not None and cancel_event.is_set():
            logger.info("[DONE] Task cancelled by the user.")
            return False

        logger.info("[STEP] %d", step)
        logger.info("Capturing screenshot...")
        try:
            screenshot = pyautogui.screenshot()
        except Exception as error:  # noqa: BLE001 - surface any capture failure
            logger.error("Could not capture the screen: %s", error)
            consecutive_errors += 1
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                logger.error("Giving up after repeated screenshot failures.")
                return False
            controller.sleep(min(2.0, 0.4 * consecutive_errors), cancel_event)
            continue

        if save_screenshots:
            try:
                screenshot.save("debug_screenshot.png")
            except OSError as error:
                logger.warning("Could not save the debug screenshot: %s", error)

        try:
            screenshot_bytes = _encode_screenshot(screenshot)
        except Exception as error:  # noqa: BLE001 - Pillow can fail on odd displays
            logger.error("Could not encode the screenshot: %s", error)
            consecutive_errors += 1
            controller.sleep(0.4, cancel_event)
            continue

        controller.wait_if_paused(cancel_event)
        logger.info("Thinking with %s...", model_name)
        request_started = time.perf_counter()
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[
                    _system_prompt(),
                    user_prompt,
                    _format_history(history),
                    "Perform the next logical step.",
                    types.Part(
                        inline_data=types.Blob(
                            mime_type="image/jpeg", data=screenshot_bytes
                        )
                    ),
                ],
                config=generate_config,
            )
        except Exception as error:  # noqa: BLE001 - API errors are expected
            elapsed = time.perf_counter() - request_started
            logger.error("Gemini request failed after %.1f s: %s", elapsed, error)
            consecutive_errors += 1
            if _is_retryable(error) and model_index + 1 < len(models_to_try):
                model_index += 1
                model_name = models_to_try[model_index]
                logger.warning("Switching to fallback model: %s", model_name)
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                logger.error("Giving up after repeated API errors.")
                return False
            controller.sleep(min(2.0, 0.5 * consecutive_errors), cancel_event)
            continue

        elapsed = time.perf_counter() - request_started
        logger.info("Model responded in %.1f s", elapsed)

        function_call = response.function_calls[0] if response.function_calls else None
        if function_call is None:
            empty_responses += 1
            text = (response.text or "").strip()
            logger.warning("The model did not return a tool call. Response: %s", text or "-")
            if empty_responses >= MAX_EMPTY_RESPONSES:
                logger.error("Giving up because the model keeps returning no action.")
                return False
            controller.sleep(0.3, cancel_event)
            continue

        empty_responses = 0
        consecutive_errors = 0

        # The model may have answered while the user pressed the pause hotkey.
        # Wait here so no new action starts until the run is resumed.
        controller.wait_if_paused(cancel_event)
        if cancel_event is not None and cancel_event.is_set():
            logger.info("[DONE] Task cancelled by the user.")
            return False

        action_name = function_call.name or ""
        action_args = dict(function_call.args) if function_call.args else {}
        try:
            serialized_args = json.dumps(action_args, ensure_ascii=True, default=str)
        except (TypeError, ValueError):
            serialized_args = str(action_args)

        # Structured marker used by the GUI to update its teaching panel.
        logger.info("[ACTION] %s %s", action_name, serialized_args)

        guide = describe_action(action_name, action_args, instant_click=instant_click)
        logger.info("%s — %s", guide.title, guide.what)
        logger.info("Why: %s", guide.why)

        try:
            if action_name == "done":
                logger.info("[DONE] Task complete. %s", guide.how)
                computer.mark_done()
                return True

            if action_name in {"click_at", "double_click_at", "move_mouse"}:
                x = int(action_args["x"])
                y = int(action_args["y"])
                if action_name == "click_at":
                    computer.click_at(x, y)
                elif action_name == "double_click_at":
                    computer.double_click_at(x, y)
                else:
                    computer.move_mouse(x, y)

            elif action_name in {"type_text_at", "type_text"}:
                text = str(action_args.get("text", ""))
                press_enter = bool(action_args.get("press_enter", False))
                if action_name == "type_text_at" and "x" in action_args and "y" in action_args:
                    computer.type_text_at(
                        int(action_args["x"]),
                        int(action_args["y"]),
                        text,
                        press_enter=press_enter,
                    )
                else:
                    computer.type_text(text, press_enter=press_enter)

            elif action_name == "press_key":
                key = normalize_key(str(action_args.get("key", "")))
                if key:
                    computer.press_key(key)

            elif action_name == "hotkey":
                raw_keys = action_args.get("keys", [])
                if isinstance(raw_keys, str):
                    raw_keys = raw_keys.split("+")
                keys = [normalize_key(str(key)) for key in raw_keys if str(key).strip()]
                if keys:
                    computer.hotkey(keys)

            else:
                logger.warning("Unknown action '%s' was ignored.", action_name)

        except Exception as error:  # noqa: BLE001 - never let one action kill the run
            consecutive_errors += 1
            logger.error("Action '%s' failed: %s", action_name, error)
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                logger.error("Giving up after repeated action failures.")
                return False
            continue

        history.append(f"- {action_name}({serialized_args})")
        if len(history) > HISTORY_LIMIT * 2:
            del history[: -HISTORY_LIMIT]

        if step_delay > 0:
            controller.sleep(step_delay, cancel_event)

    logger.warning("[DONE] Reached the step limit of %d steps.", max_steps)
    return False


def run_agent_with_pause(user_prompt: str, **kwargs: Any) -> bool:
    """Run the agent with the global Alt+F10 pause/resume hotkey enabled."""
    controller = PauseController()
    controller.start()
    try:
        return run_agent(user_prompt, pause_controller=controller, **kwargs)
    finally:
        controller.stop()


def main(argv: list[str] | None = None) -> int:
    """Small compatibility entry point for running the agent directly."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        logger.error("Usage: python agent.py \"your goal\"")
        return 2
    success = run_agent_with_pause(" ".join(argv))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
