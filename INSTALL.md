# Installation Guide

This guide will walk you through the step-by-step installation of the Desktop Computer Use Agent.

## System Requirements

- **Operating System**: Windows 11, Windows 10, macOS, or Linux
- **Python**: Version 3.8 or higher
- **Anaconda/Miniconda**: For virtual environment management
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
conda create -n computer-use-desktop python=3.10
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
- `google-generativeai` - Gemini API
- `pyautogui` - Desktop automation
- `Pillow` - Image processing
- `python-dotenv` - Environment variables

## Step 6: Set Up Google Gemini API Key

### Get API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Create a new API key
4. Copy the API key

### Create .env File

Create a new file named `.env` in the project directory:

```bash
# Windows
copy .env.example .env

# Or create manually
notepad .env
```

Add the following content:

```
GEMINI_API_KEY=YOUR_API_KEY_HERE
```

Replace `YOUR_API_KEY_HERE` with your actual API key.

## Step 7: Test Installation

Run a simple test:

```bash
python main.py "Show me the time"
```

If everything is installed correctly, the agent should start and attempt to execute the task.

## Troubleshooting

### "GEMINI_API_KEY not found"

- Make sure the `.env` file exists in the project directory
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

- Read the [README.md](README.md) for usage examples
- Experiment with different commands
- Customize the system prompt in `agent.py` to your needs

## Support

If you encounter problems:
1. Check the logs in `computer-use.log`
2. Look at `debug_screenshot.png`
3. Open an issue on GitHub

---

**Good luck with the Desktop Computer Use Agent!**
