# Installation Guide

This guide will walk you through the step-by-step installation of the Desktop Computer Use Agent.

## System Requirements

- **Operating System**: Windows 11, Windows 10, macOS, or Linux
- **Python**: Version 3.13 (the launcher uses `py -3.13`)
- **Anaconda/Miniconda**: Optional, for virtual environment management
- **Internet**: For API access to Google Gemini

**Note**: For macOS and Linux users, you need to modify the `SYSTEM_PROMPT` in `agent.py` to specify your operating system. See the Configuration section in [README.md](README.md).

## Step 1: Install Anaconda/Miniconda

If not already installed, download Anaconda or Miniconda:

- **Anaconda**: https://www.anaconda.com/download
- **Miniconda** (recommended, smaller): https://docs.conda.io/en/latest/miniconda.html

## Step 2: Download Repository

### Option A: Using Git

```bash
git clone https://github.com/YOUR_USERNAME/pc-use.git
cd pc-use
```

### Option B: ZIP Download

1. Download the repository as ZIP
2. Extract the file
3. Open a terminal in the extracted folder

## Step 3: Create Conda Environment

Open Anaconda Prompt or a terminal and run:

```bash
conda create -n computer-use-desktop python=3.13
```

Confirm the installation with `y` when prompted.

## Step 4: Activate Conda Environment

```bash
conda activate computer-use-desktop
```

**Important**: This environment must be activated every time before running the program.

## Step 5: Install Dependencies

Make sure you're in the project directory and run:

```bash
pip install -r requirements.txt
```

This installs the following packages:
- `google-genai` - Gemini API
- `PyQt6` - Graphical interface
- `pyautogui` - Desktop automation
- `Pillow` - Image processing
- `python-dotenv` - Environment variables

## Step 6: Set Up Google Gemini API Key

### Get API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Create a new API key
4. Copy the API key

### Save the Key in the System Configuration

The GUI and the command line share one per-user configuration file, so you only
need to save the key once:

- **GUI:** start `py -3.13 main.py`, paste the key into the API key field, and
  press **Save**. The field is pre-filled automatically the next time you open
  the window.
- **CLI:** save the key directly and exit:

  ```bash
  py -3.13 main.py --save-key --api-key "YOUR_API_KEY_HERE"
  ```

  Remove it again with:

  ```bash
  py -3.13 main.py --forget-key
  ```

On Windows the key is stored in
`%APPDATA%\GeminiPCUse\config.json`. On macOS and Linux the equivalent per-user
configuration directory is used. The key never lives in the project directory.

### Optional .env Fallback

If you prefer a project-local file, copy `.env.example` to `.env` and set:

```
GEMINI_API_KEY=YOUR_API_KEY_HERE
```

This is optional. The system configuration takes priority, and `.env` files are
ignored by Git.

## Step 7: Test Installation

Start the graphical interface:

```bash
py -3.13 main.py
```

Paste your API key into the key field, describe a goal, and press **Start task**.

You can also run a task directly from the command line:

```bash
py -3.13 main.py "Show me the time"
```

If everything is installed correctly, the agent should start and attempt to execute the task. The GUI shows a live log and explains every action in the teaching panel.

While a task is running, press `Alt+F10` anywhere in Windows to pause or
resume it. The GUI Pause button sends the same signal.

## Troubleshooting

### "GEMINI_API_KEY not found"

- Save the key in the GUI, or run `py -3.13 main.py --save-key --api-key "YOUR_KEY"`
- Alternatively, set the `GEMINI_API_KEY` environment variable or create a `.env` file
- Verify the API key is correctly entered
- Don't use quotes around the API key

### "ModuleNotFoundError"

- Ensure the Conda environment is activated:
  ```bash
  conda activate computer-use-desktop
  ```
- Reinstall dependencies:
  ```bash
  pip install -r requirements.txt
  ```

### PyQt6 not installed

```bash
py -3.13 -m pip install PyQt6
```

### Wrong model

The default model is `gemini-3.5-flash-lite`. Choose another model in the GUI,
or pass `--model` on the command line. The combo box is editable, so you can
type any model name your API key has access to.

### Pyautogui not working

- Ensure no other programs are blocking mouse/keyboard
- Run the program with administrator rights (if necessary)

### API Errors

- Check your internet connection
- Verify the API key is valid
- Check if you have API quota remaining

## Uninstallation

To remove the installation:

```bash
# Deactivate Conda environment
conda deactivate

# Remove Conda environment
conda env remove -n computer-use-desktop

# Delete project folder
# (manually in Explorer)
```

## Next Steps

- Read the [README.md](README.md) for GUI and command-line examples
- Experiment with different commands and models
- Turn on **Instant click** for faster runs
- Customize the system prompt in `agent.py` to your needs

## Support

If you encounter problems:
1. Check the logs in `computer-use.log`
2. Look at `debug_screenshot.png`
3. Open an issue on GitHub

---

**Good luck with the Desktop Computer Use Agent!**
