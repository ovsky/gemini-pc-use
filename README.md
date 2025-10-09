# Desktop Computer Use Agent

An AI-powered desktop automation agent that uses Google's Gemini 2.5 Computer-Use model to autonomously execute Windows/macOS/Linux desktop tasks through natural language commands.

## 🎯 Description

This agent enables autonomous control of your desktop using AI. It continuously takes screenshots, sends them to the Gemini model, and executes desktop actions (clicking, double-clicking, typing text, pressing keys) based on AI decisions.

**Platform Support**: Works on Windows 11, macOS, and Linux. For macOS/Linux, you need to adjust the `SYSTEM_PROMPT` in `agent.py` to match your operating system.

## ✨ Features

- 🤖 Autonomous desktop control via Gemini 2.5 Computer-Use
- 🖱️ Mouse and keyboard control with pyautogui
- 📸 Screenshot-based visual analysis
- 📝 Action history for context-aware decisions
- 🎯 Normalized coordinates for different screen resolutions
- 🔄 Continuous loop until goal achievement

## 📋 Prerequisites

- Python 3.8 or higher
- Anaconda or Miniconda
- Windows 11, macOS, or Linux
- Google Gemini API Key

## 🚀 Installation

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/pc-use.git
cd pc-use
```

### 2. Create Conda environment

```bash
conda create -n computer-use-desktop python=3.10
conda activate computer-use-desktop
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project directory:

```bash
GEMINI_API_KEY=your_gemini_api_key_here
```

You can create an API key at [Google AI Studio](https://makersuite.google.com/app/apikey).

## 💻 Usage

### Basic usage

```bash
python main.py "Open notepad and write a letter"
```

### Examples

```bash
# File operations
python main.py "Create a new folder on the desktop named 'Projects'"

# Opening applications
python main.py "Open Chrome browser and go to google.com"

# Complex tasks
python main.py "Open Excel and create a new spreadsheet with sample data"
```

## 📁 Project Structure

```
pc-use/
├── main.py              # Main entry point
├── agent.py             # Agent logic and Gemini integration
├── computer.py          # Desktop control functions
├── logging_config.py    # Logging configuration
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (not in repository)
└── README.md           # This file
```

## ⚙️ How It Works

1. **Screenshot**: The agent takes a screenshot of the current screen
2. **Analysis**: The screenshot is sent to Gemini along with the user's goal
3. **Decision**: The model decides on the next action to execute
4. **Execution**: The action is executed using pyautogui
5. **Repeat**: Steps 1-4 are repeated until the goal is achieved

## 🛠️ Available Actions

- `click_at(x, y)`: Single mouse click at coordinates
- `double_click_at(x, y)`: Double-click at coordinates
- `type_text_at(x, y, text)`: Type text at position
- `press_key(key)`: Press a key (e.g., 'enter', 'esc')
- `move_mouse(x, y)`: Move mouse without clicking
- `done()`: Mark task as completed

## ⚠️ Important Notes

- **Caution**: The agent has full control over mouse and keyboard
- Make sure not to interfere during execution
- The agent uses normalized coordinates (0-1000)
- Screenshots are saved as `debug_screenshot.png`
- All actions are logged in `computer-use.log`

## 🔧 Configuration

### Platform-Specific Setup (macOS/Linux)

If you're using macOS or Linux, you **must** modify the `SYSTEM_PROMPT` in `agent.py` to match your operating system:

```python
# For macOS
SYSTEM_PROMPT = """
You are operating a macOS desktop. Your task is to achieve the goal specified by the user by executing a series of actions.
...
"""

# For Linux
SYSTEM_PROMPT = """
You are operating a Linux desktop. Your task is to achieve the goal specified by the user by executing a series of actions.
...
"""
```

### Customize System Prompt

The system prompt in `agent.py` can be customized to change the agent's behavior:

```python
SYSTEM_PROMPT = """
Your custom instructions here...
"""
```

### Adjust Wait Times

In `agent.py`, you can change the wait time between actions:

```python
time.sleep(5)  # Wait time in seconds
```

## 🐛 Troubleshooting

### Agent performs wrong actions
- Check saved screenshots in `debug_screenshot.png`
- Review logs in `computer-use.log`

### API errors
- Ensure your GEMINI_API_KEY is valid
- Check your internet connection

### Mouse doesn't move
- Verify pyautogui is correctly installed
- Disable other mouse/keyboard programs

## 📝 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## 🤝 Contributing

Contributions are welcome! Please create a pull request or open an issue for suggestions.

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## ⚖️ Disclaimer

This tool gives the AI model full control over your desktop. Use at your own risk. The author assumes no liability for damages arising from the use of this tool.

## 📧 Contact

For questions or issues, please open an issue on GitHub.

---

**Note**: This project uses the experimental Gemini 2.5 Computer-Use API and may change when Google releases updates.
