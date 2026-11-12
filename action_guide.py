"""Human-readable explanations for every action the agent can take.

The GUI reuses these explanations to teach the user what just happened, why
the agent did it, and how the underlying mechanism works.
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
    x = args.get("x", "?")
    y = args.get("y", "?")
    return f"({x}, {y})"


def _shorten(text: Any, limit: int = 90) -> str:
    value = str(text)
    if len(value) <= limit:
        return value
    return value[: limit - 1] + "…"


def _keys(args: dict[str, Any]) -> str:
    keys = args.get("keys", "")
    if isinstance(keys, (list, tuple)):
        return " + ".join(str(key) for key in keys) or "?"
    return str(keys)


def overview() -> Guide:
    return Guide(
        title="Ready when you are",
        what=(
            "The agent works in a loop: it looks at your screen, decides on one "
            "small action, performs it, and checks the result."
        ),
        why=(
            "Desktop apps rarely offer a reliable API. Vision plus synthetic "
            "mouse and keyboard input lets the agent operate almost any "
            "program, including ones that were never designed for automation."
        ),
        how=(
            "Each turn, a screenshot is sent to Gemini. Gemini answers with a "
            "single tool call, for example a click at normalized coordinates. "
            "The agent maps those coordinates to your real screen, performs the "
            "action, and sends a fresh screenshot next turn."
        ),
        tip=(
            "Describe the goal, not every click. Narrow goals finish faster and "
            "are easier for the agent to verify."
        ),
    )


def thinking(step: int) -> Guide:
    return Guide(
        title=f"Step {step}: observing the screen",
        what="Capturing a screenshot and asking Gemini what to do next.",
        why=(
            "The screenshot is the agent's only source of truth. Looking again "
            "after every action lets it notice dialogs, loading states, and "
            "mistakes instead of blindly following a fixed script."
        ),
        how=(
            "The image is downscaled to keep the request small, encoded as JPEG, "
            "and sent together with the goal, the system rules, and a short "
            "history of recent actions."
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
            "The pointer jumps straight to the target and clicks without a "
            "travel animation."
            if instant_click
            else "The pointer glides to the target, then clicks once."
        )
        return Guide(
            title="Single click",
            what=f"Clicking once at normalized screen position {coordinates}.",
            why=(
                "One click focuses a text field, selects a row, or presses a "
                "button. It is the most common way to move the interface "
                "forward when no keyboard shortcut exists."
            ),
            how=(
                "Gemini receives a screenshot and answers with coordinates on a "
                "0–1000 grid. The agent multiplies them by your real resolution, "
                f"moves the pointer, and clicks. {motion}"
            ),
            tip=(
                "A miss is not fatal: the next screenshot shows the result, so "
                "the model can correct the next click."
            ),
        )

    if name == "double_click_at":
        return Guide(
            title="Double click",
            what=f"Double-clicking at normalized screen position {coordinates}.",
            why=(
                "Double clicks open desktop icons, files, and folders, or enter "
                "edit mode in some applications. A single click would only "
                "select the item."
            ),
            how=(
                "The coordinates are converted to pixels and two clicks are sent "
                "in quick succession at the same point."
            ),
            tip=(
                "If an icon does not open, the model can retry or use the "
                "keyboard, for example Enter after selecting the icon."
            ),
        )

    if name == "type_text_at":
        text = _shorten(args.get("text", ""))
        enter = " It then presses Enter." if args.get("press_enter") else ""
        return Guide(
            title="Click and type",
            what=f"Clicking at {coordinates} and typing: “{text}”.{enter}",
            why=(
                "Typing needs a focused input. Clicking first guarantees that "
                "the text lands in the intended field instead of wherever the "
                "caret happened to be."
            ),
            how=(
                "The agent clicks the target, then sends the characters as "
                "keyboard events. Enter is pressed afterwards when the model "
                "asks for it, which submits forms and search boxes."
            ),
            tip=(
                "The model usually clears existing text with Ctrl+A and "
                "Backspace before typing, so old content is replaced."
            ),
        )

    if name == "type_text":
        text = _shorten(args.get("text", ""))
        enter = " It then presses Enter." if args.get("press_enter") else ""
        return Guide(
            title="Type at the current focus",
            what=f"Typing into the already focused control: “{text}”.{enter}",
            why=(
                "When the correct field is already focused, clicking again can "
                "move the caret or close a menu. Typing directly is faster and "
                "safer."
            ),
            how="Characters are sent as keyboard events to the active window.",
            tip="Useful right after a hotkey such as Win+R opened the Run dialog.",
        )

    if name == "press_key":
        key = args.get("key", "?")
        return Guide(
            title="Press a key",
            what=f"Pressing the {key} key.",
            why=(
                "Keys confirm dialogs, dismiss popups, move focus, and submit "
                "forms. Enter and Escape are especially useful for unblocking "
                "the current screen."
            ),
            how=(
                "The key name is normalized to a PyAutoGUI key (for example "
                "Return becomes Enter) and sent to the active window."
            ),
            tip="Escape is a safe way to close an unexpected menu or dialog.",
        )

    if name == "hotkey":
        combo = _keys(args)
        return Guide(
            title="Keyboard shortcut",
            what=f"Pressing the shortcut {combo}.",
            why=(
                "Shortcuts are the fastest and most reliable way to drive "
                "Windows. Win+R opens the Run dialog, Ctrl+S saves, and "
                "Alt+Tab switches windows — without hunting for pixels."
            ),
            how=(
                "All keys are held down together in order and released in "
                "reverse order, exactly like a real key combination."
            ),
            tip="Win+R followed by typing an app name is often faster than the Start menu.",
        )

    if name == "move_mouse":
        return Guide(
            title="Move the pointer",
            what=f"Moving the pointer to normalized position {coordinates}.",
            why=(
                "Sometimes the interface only reacts to hover, for example to "
                "reveal a tooltip or a hidden toolbar."
            ),
            how="The pointer is moved without pressing any mouse button.",
            tip="Most tasks can skip this step by using instant click mode.",
        )

    if name == "done":
        return Guide(
            title="Task complete",
            what="The model decided that the goal has been reached and ended the run.",
            why=(
                "Stopping explicitly prevents wasted API calls and prevents the "
                "agent from continuing to click after the job is finished."
            ),
            how=(
                "Gemini calls the done tool. The agent stops the loop, writes the "
                "final status to the log, and releases the keyboard and mouse."
            ),
            tip="Check the result yourself; the agent reports success, not perfection.",
            tone="success",
        )

    return Guide(
        title="Unknown action",
        what=f"The model requested “{name}”, which this client does not implement.",
        why="Unsupported actions are ignored so a single bad tool call cannot crash the run.",
        how="The agent logs a warning and asks for the next step using a fresh screenshot.",
        tip="Update the tool list in agent.py if you need a new capability.",
        tone="warn",
    )


def failure(message: str) -> Guide:
    return Guide(
        title="The run stopped",
        what=_shorten(message, 240),
        why=(
            "A clear failure is better than silently clicking in circles. The "
            "log below contains the exact error from the agent."
        ),
        how=(
            "Check the API key, your internet connection, and the model name. "
            "Then start the task again."
        ),
        tip="The last screenshot is saved as debug_screenshot.png when debug mode is on.",
        tone="error",
    )
