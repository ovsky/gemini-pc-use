# Gemini PC Use

Control your desktop with a Gemini vision agent. The agent takes a screenshot,
asks Gemini for the next action, performs it with PyAutoGUI, and repeats until
the goal is complete.

This version adds a polished desktop GUI, a live teaching panel that explains
every action, persistent API key storage, model selection, instant click mode,
and a much faster agent loop.

> **Default model:** `gemini-3.5-flash-lite`

---

## Highlights

- **Beautiful desktop GUI** — dark, modern PyQt6 interface with a task editor,
  example prompts, status pill, step counter, and elapsed timer.
- **Live log panel** — every agent message streams into the window in real time,
  colour-coded by level.
- **Teaching panel** — explains the current action in four parts:
  *What happened*, *why it matters*, *how it works*, and *try this*.
- **Persistent API key** — saved to a per-user system file, never to the project
  directory. The GUI can also read `GEMINI_API_KEY` from your environment or an
  env file.
- **Model picker** — choose any Gemini model. `gemini-3.5-flash-lite` is the
  default; the combo box is editable.
- **Instant click mode** — click directly on the target point without animating
  the pointer across the screen. Roughly halves the time spent per mouse action.
- **Faster loop** — fixed two-second sleeps removed, one reusable Gemini client,
  downscaled JPEG screenshots, trimmed action history, shorter typing interval,
  and automatic fallback only when an API error actually happens.
- **Safe cancellation** — Stop kills the child process immediately and releases
  keyboard and mouse control.
- **English only** — all comments, prompts, docstrings, and user-facing text have
  been translated to English.

---

## Requirements

- Windows 10/11 (macOS and Linux also work; update the system prompt if the
  desktop differs)
- Python 3.13 (the GUI is launched with `py -3.13`)
- A Google Gemini API key

---

## Installation

### 1. Install Python dependencies

```bash
py -3.13 -m pip install -r requirements.txt
```

If you prefer Conda:

```bash
conda create -n computer-use-desktop python=3.13
conda activate computer-use-desktop
pip install -r requirements.txt
```

### 2. Start the GUI

```bash
py -3.13 main.py
```

Or explicitly:

```bash
py -3.13 main.py --gui
```

### 3. Add your API key

Paste your key into the **Gemini API key** field. Create one at
<https://aistudio.google.com/app/apikey>.

The key is stored at:

| Platform | Location |
| --- | --- |
| Windows | `%APPDATA%\GeminiPCUse\config.json` |
| macOS | `~/Library/Application Support/GeminiPCUse/config.json` |
| Linux | `~/.config/gemini-pc-use/config.json` |

Use the **Config folder** button in the footer to open that directory. Uncheck
**Remember this key on this computer** to keep it for the current session only.

---

## Using the GUI

1. Describe the goal in the task box, or pick an example chip.
2. Choose a model. The default is `gemini-3.5-flash-lite`.
3. Leave **Instant click** on for maximum speed. Turn it off if you want to watch
   the pointer move before each click.
4. Press **Start task** (or `Ctrl+Enter`).
5. Watch the live log and the teaching panel. The panel updates after every
   action so you can see exactly what the agent decided and why.
6. Press **Stop** (or `Esc`) at any time.

The footer always shows the exact command that will be executed, for example:

```text
py -3.13 main.py "Open Notepad and type a short welcome message." --model gemini-3.5-flash-lite --instant-click
```

---

## Command-line usage

The GUI is optional. The agent still works as a normal command-line program:

```bash
py -3.13 main.py "Open Notepad and type a short poem"
```

Useful options:

```bash
py -3.13 main.py "goal" --model gemini-3.5-flash-lite
py -3.13 main.py "goal" --instant-click
py -3.13 main.py "goal" --no-instant-click
py -3.13 main.py "goal" --max-steps 40
py -3.13 main.py "goal" --step-delay 0
py -3.13 main.py "goal" --debug-screenshots
py -3.13 main.py "goal" --verbose
py -3.13 main.py --help
```

The API key is resolved in this order:

1. `--api-key` argument
2. `GEMINI_API_KEY` environment variable
3. the saved GUI configuration
4. `.env`, `GEMINI_API_KEY.env`, or `enviro.env` in the project directory

---

## Speed

The original loop waited two seconds after every step, saved a full-resolution
screenshot to disk on every step, and recreated the Gemini client each run.
Those costs are gone. Current behaviour:

- No fixed post-step delay (default `0.1` seconds, configurable with
  `--step-delay 0`).
- Screenshots are downscaled to at most 1280×720 and JPEG-encoded once.
- Action history is capped at the 12 most recent steps.
- Typing interval reduced to 15 ms.
- `pyautogui.PAUSE` reduced to 30 ms.
- Instant click skips pointer travel entirely.
- Model fallback is attempted only after a real retryable API error.
- Debug screenshots are opt-in with `--debug-screenshots`.

Model latency usually dominates a run, so a faster model has the largest
effect. `gemini-3.5-flash-lite` is the recommended default.

---

## How the agent works

```text
screenshot -> Gemini -> one tool call -> PyAutoGUI -> screenshot -> ...
```

Gemini receives:

- the system rules,
- your goal,
- a short history of recent actions,
- the current screenshot.

It replies with exactly one tool call:

| Tool | Purpose |
| --- | --- |
| `click_at` | Single left click at normalized coordinates (0–1000) |
| `double_click_at` | Open icons, files, folders |
| `type_text_at` | Focus a point, type text, optional Enter |
| `type_text` | Type into the already focused control |
| `press_key` | Press Enter, Tab, Escape, Win, and other keys |
| `hotkey` | Key combinations such as Win+R or Ctrl+S |
| `done` | Finish the task |

Coordinates are normalized so the same prompt works on any screen resolution.

---

## Configuration file

The GUI writes JSON similar to:

```json
{
  "api_key": "your-key",
  "model": "gemini-3.5-flash-lite",
  "instant_click": true,
  "remember_api_key": true,
  "max_steps": 80,
  "step_delay": 0.1,
  "save_screenshots": false
}
```

The file is written atomically and permission-restricted where the platform
supports it.

---

## Safety

- The agent controls the real mouse and keyboard. Keep an eye on it.
- `Esc` stops the run from the GUI.
- PyAutoGUI fail-safe is disabled so the agent can reach screen corners. Do not
  rely on slamming the pointer into a corner to stop it; use **Stop**.
- Never commit your API key. The GUI stores it outside the repository, but the
  legacy `GEMINI_API_KEY.env` and `enviro.env` files in this checkout may still
  contain a key that is tracked by Git. Rotate the key and remove those files
  from version control if that applies to you.

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'PyQt6'`**

```bash
py -3.13 -m pip install PyQt6
```

**The GUI says the API key is missing**

Paste the key in the GUI, or set it before starting:

```powershell
$env:GEMINI_API_KEY = "your-key"
py -3.13 main.py
```

**Clicks land in the wrong place**

- Keep the display scaling at 100% if possible.
- Try animated mode (`--no-instant-click`) to see where the pointer goes.
- Run with `--debug-screenshots` to inspect what the model saw.

**The model returns no action**

- Check your quota and internet connection.
- Try another model in the combo box.
- Restart the task with a narrower goal.

**Logs**

- The GUI shows logs live.
- A rotating log is written to `computer-use.log`.

---

## Project structure

```text
main.py              CLI entry point and GUI launcher
agent.py             Gemini agent loop and tool definitions
computer.py          PyAutoGUI desktop actions
config.py            Settings and API key persistence
action_guide.py      Human-readable explanations for the teaching panel
logging_config.py    Console and rotating file logging
frontend/app.py      PyQt6 graphical interface
backend/agent.py     Text-only Gemini helper
INSTALL.md           Detailed installation guide
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Contributions are welcome.

## License

MIT — see [LICENSE](LICENSE).
