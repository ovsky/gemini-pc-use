"""Human-readable explanations for every action the agent can take.

The GUI reuses these explanations to teach the user what just happened, why
the agent did it, and how the underlying mechanism works. The texts are kept
short enough to fit comfortably in the teaching panel.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Guide:
    title: str
    what: str
    why: str
    how: str
    tip: str = ""
    tone: str = "info"  # info | success | warn | error

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


def _coord(args: dict[str, Any]) -> str:
    return f"({args.get('x', '?')}, {args.get('y', '?')})"


def _shorten(text: Any, limit: int = 70) -> str:
    value = str(text)
    return value if len(value) <= limit else value[: limit - 1] + "…"


def _keys(args: dict[str, Any]) -> str:
    keys = args.get("keys", "")
    if isinstance(keys, (list, tuple)):
        return " + ".join(str(key) for key in keys) or "?"
    return str(keys)


def overview() -> Guide:
    return Guide(
        title="Ready when you are",
        what=(
            "The agent looks at your screen, chooses one small action, performs "
            "it, then looks again."
        ),
        why=(
            "Most desktop apps have no reliable API. Vision plus synthetic "
            "input can operate almost any program."
        ),
        how=(
            "Each turn, a screenshot goes to Gemini. Gemini returns one tool "
            "call; the agent maps it to your real screen and runs it."
        ),
        tip=(
            "Describe the goal, not every click. Narrow goals finish faster."
        ),
    )


def thinking(step: int) -> Guide:
    return Guide(
        title=f"Step {step}: observing the screen",
        what="Capturing a screenshot and asking Gemini what to do next.",
        why=(
            "Looking again after every action lets the agent notice dialogs, "
            "loading states, and mistakes."
        ),
        how=(
            "The image is downscaled to 1280×720, JPEG-encoded, and sent with "
            "the goal, the rules, and recent history."
        ),
        tip="Keep the target window visible and avoid switching apps mid-run.",
    )


def describe_action(
    name: str,
    args: dict[str, Any] | None = None,
    *,
    instant_click: bool = False,
) -> Guide:
    """Return a teaching explanation for one tool call."""
    args = args or {}
    coordinates = _coord(args)

    if name == "click_at":
        motion = (
            "The pointer jumps straight to the target and clicks."
            if instant_click
            else "The pointer glides to the target, then clicks once."
        )
        return Guide(
            title="Single click",
            what=f"Clicking once at normalized screen position {coordinates}.",
            why=(
                "One click focuses a field, selects an item, or presses a "
                "button — the usual way to move forward without a shortcut."
            ),
            how=(
                "Gemini answers on a 0–1000 grid; the agent maps the point to "
                f"your resolution. {motion}"
            ),
            tip="A miss is not fatal: the next screenshot lets the model correct it.",
        )

    if name == "double_click_at":
        return Guide(
            title="Double click",
            what=f"Double-clicking at normalized screen position {coordinates}.",
            why=(
                "Double clicks open desktop icons, files, and folders. A single "
                "click would only select the item."
            ),
            how=(
                "The point is converted to pixels and two quick clicks are sent "
                "at the same spot."
            ),
            tip="If an icon does not open, the model can select it and press Enter.",
        )

    if name == "type_text_at":
        text = _shorten(args.get("text", ""))
        enter = " Then it presses Enter." if args.get("press_enter") else ""
        return Guide(
            title="Click and type",
            what=f"Clicking at {coordinates} and typing “{text}”.{enter}",
            why=(
                "Typing needs focus. Clicking first guarantees the text lands in "
                "the intended field, not wherever the caret was."
            ),
            how=(
                "The agent clicks, sends the characters as key events, and "
                "presses Enter when requested — ready for forms and search."
            ),
            tip="The model often clears the field with Ctrl+A and Backspace first.",
        )

    if name == "type_text":
        text = _shorten(args.get("text", ""))
        enter = " Then it presses Enter." if args.get("press_enter") else ""
        return Guide(
            title="Type at the current focus",
            what=f"Typing into the focused control: “{text}”.{enter}",
            why=(
                "When the right field already has focus, clicking again can move "
                "the caret or close a menu."
            ),
            how="Characters are sent as keyboard events to the active window.",
            tip="Useful right after Win+R opened the Run dialog.",
        )

    if name == "press_key":
        key = args.get("key", "?")
        return Guide(
            title="Press a key",
            what=f"Pressing the {key} key.",
            why=(
                "Keys confirm dialogs, dismiss popups, move focus, and submit "
                "forms. Enter and Escape are the best unblockers."
            ),
            how=(
                "The key name is normalized to a PyAutoGUI key and sent to the "
                "active window."
            ),
            tip="Escape is a safe way to close an unexpected menu or dialog.",
        )

    if name == "hotkey":
        combo = _keys(args)
        return Guide(
            title="Keyboard shortcut",
            what=f"Pressing the shortcut {combo}.",
            why=(
                "Shortcuts are the fastest, most reliable way to drive Windows — "
                "no pixel hunting required."
            ),
            how=(
                "All keys are held together in order, then released in reverse, "
                "exactly like a real key combination."
            ),
            tip="Win+R plus an app name is often faster than the Start menu.",
        )

    if name == "move_mouse":
        return Guide(
            title="Move the pointer",
            what=f"Moving the pointer to normalized position {coordinates}.",
            why=(
                "Some interfaces only react to hover, for example to reveal a "
                "tooltip or a hidden toolbar."
            ),
            how="The pointer is moved without pressing any mouse button.",
            tip="Most tasks can skip this by using instant click mode.",
        )

    if name == "done":
        return Guide(
            title="Task complete",
            what="The model decided the goal is reached and ended the run.",
            why=(
                "Stopping explicitly prevents wasted API calls and extra clicks "
                "after the job is finished."
            ),
            how=(
                "Gemini calls the done tool. The agent stops the loop, logs the "
                "result, and releases keyboard and mouse control."
            ),
            tip="Check the result yourself; the agent reports success, not perfection.",
            tone="success",
        )

    return Guide(
        title="Unknown action",
        what=f"The model requested “{name}”, which this client does not implement.",
        why="Unsupported actions are ignored so one bad tool call cannot crash the run.",
        how="The agent logs a warning and asks for the next step with a fresh screenshot.",
        tip="Add the capability to the tool list in agent.py.",
        tone="warn",
    )


def paused() -> Guide:
    return Guide(
        title="Agent paused",
        what="The run is frozen before its next action.",
        why=(
            "You can step away, inspect the screen, or take over the mouse "
            "without the agent clicking somewhere unexpected."
        ),
        how=(
            "Press Alt+F10 again, or click Resume, to continue from the same "
            "step. The agent never starts a new action while paused."
        ),
        tip="The shortcut is global, so it works even when this window is in the background.",
        tone="warn",
    )


def resumed(step: int = 0) -> Guide:
    title = f"Step {step}: resumed" if step else "Agent resumed"
    return Guide(
        title=title,
        what="The agent is running again.",
        why=(
            "Continuing from the same point avoids repeating actions that were "
            "already completed before the pause."
        ),
        how=(
            "The pause flag was cleared; the next screenshot and model call "
            "happen immediately."
        ),
        tip="Press Alt+F10 at any time to pause again.",
        tone="success",
    )


def failure(message: str) -> Guide:
    return Guide(
        title="The run stopped",
        what=_shorten(message, 180),
        why=(
            "A clear failure is better than silently clicking in circles. The "
            "log below contains the exact error."
        ),
        how=(
            "Check the API key, internet connection, and model name, then start "
            "the task again."
        ),
        tip="Enable debug screenshots to see exactly what the model saw.",
        tone="error",
    )
