"""Application configuration and API key persistence.

The GUI stores its settings in a per-user configuration file so that the
project directory stays clean and the API key is not committed by accident.

Locations:
    Windows: %APPDATA%\\GeminiPCUse\\config.json
    macOS:   ~/Library/Application Support/GeminiPCUse/config.json
    Linux:   ~/.config/gemini-pc-use/config.json

Set GEMINI_PC_USE_CONFIG to override the path (useful for tests).
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

APP_NAME = "GeminiPCUse"
DEFAULT_MODEL = "gemini-3.5-flash-lite"

# Models offered in the GUI. The combo box is editable, so any model name can
# be typed in manually as well.
KNOWN_MODELS = [
    DEFAULT_MODEL,
    "gemini-3.5-flash",
    "gemini-3.0-flash",
    "gemini-3.0-flash-lite",
]

PROJECT_ROOT = Path(__file__).resolve().parent
ENV_FILES = (".env", "GEMINI_API_KEY.env", "enviro.env")
DEFAULT_STEP_DELAY = 0.1
DEFAULT_MAX_STEPS = 80

DEFAULT_CONFIG: dict[str, Any] = {
    "api_key": "",
    "model": DEFAULT_MODEL,
    "instant_click": False,
    "remember_api_key": True,
    "max_steps": DEFAULT_MAX_STEPS,
    "step_delay": DEFAULT_STEP_DELAY,
    "save_screenshots": False,
}


def _config_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home())
        return Path(base) / APP_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "gemini-pc-use"


def config_path() -> Path:
    """Return the active configuration file path."""
    override = os.environ.get("GEMINI_PC_USE_CONFIG")
    if override:
        return Path(override).expanduser()
    return _config_dir() / "config.json"


def load_config() -> dict[str, Any]:
    """Load settings, filling in defaults for missing or invalid values."""
    config = dict(DEFAULT_CONFIG)
    path = config_path()
    try:
        with path.open("r", encoding="utf-8") as handle:
            stored = json.load(handle)
        if isinstance(stored, dict):
            config.update({key: value for key, value in stored.items() if key in config})
    except FileNotFoundError:
        pass
    except (OSError, ValueError):
        # A corrupt config should never stop the application from starting.
        pass

    if not isinstance(config.get("api_key"), str):
        config["api_key"] = ""
    if not isinstance(config.get("model"), str) or not config["model"].strip():
        config["model"] = DEFAULT_MODEL
    config["instant_click"] = bool(config.get("instant_click", False))
    config["remember_api_key"] = bool(config.get("remember_api_key", True))
    config["save_screenshots"] = bool(config.get("save_screenshots", False))
    try:
        config["max_steps"] = max(1, int(config.get("max_steps", DEFAULT_MAX_STEPS)))
    except (TypeError, ValueError):
        config["max_steps"] = DEFAULT_MAX_STEPS
    try:
        config["step_delay"] = max(0.0, float(config.get("step_delay", DEFAULT_STEP_DELAY)))
    except (TypeError, ValueError):
        config["step_delay"] = DEFAULT_STEP_DELAY
    return config


def save_config(config: dict[str, Any]) -> Path:
    """Persist settings atomically and restrict the file to the current user."""
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = dict(DEFAULT_CONFIG)
    payload.update(config)
    if not payload.get("remember_api_key"):
        payload["api_key"] = ""

    descriptor, temporary_name = tempfile.mkstemp(
        prefix="config-", suffix=".json", dir=str(path.parent)
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)

    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return path


def load_env_files() -> None:
    """Load the environment files that exist in the project directory.

    The project historically shipped several differently named env files. All
    of them are supported so existing installations keep working.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    for filename in ENV_FILES:
        candidate = PROJECT_ROOT / filename
        if candidate.exists():
            load_dotenv(candidate, override=False)


def api_key_from_env_files() -> str:
    """Read an API key from the supported env files without importing dotenv."""
    for filename in ENV_FILES:
        candidate = PROJECT_ROOT / filename
        if not candidate.exists():
            continue
        try:
            for raw_line in candidate.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                name, value = line.split("=", 1)
                if name.strip() == "GEMINI_API_KEY":
                    value = value.strip().strip('"').strip("'")
                    if value and value != "your_api_key_here":
                        return value
        except OSError:
            continue
    return ""


def resolve_api_key(config: dict[str, Any] | None = None) -> str:
    """Resolve the API key from the environment, saved config, or env files."""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        return key
    if config is None:
        config = load_config()
    key = str(config.get("api_key", "")).strip()
    if key:
        return key
    return api_key_from_env_files()
