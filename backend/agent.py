"""Small text-only Gemini helper used by the backend layer.

The desktop agent lives in the project-level ``agent.py``. This module is kept
for integrations that only need a plain text completion.
"""

from __future__ import annotations

import logging

from google import genai

from config import DEFAULT_MODEL, load_env_files, resolve_api_key

logger = logging.getLogger(__name__)


def ask_gemini(prompt: str, model: str | None = None) -> str:
    """Send a text prompt to Gemini and return the response text."""
    load_env_files()
    api_key = resolve_api_key()
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY was not found. Add it in the GUI, in your "
            "environment, or in a .env file."
        )

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model or DEFAULT_MODEL,
        contents=prompt,
    )
    return response.text or ""


def run_agent(user_prompt: str, model: str | None = None) -> str:
    """Backward-compatible alias for :func:`ask_gemini`."""
    return ask_gemini(user_prompt, model=model)
