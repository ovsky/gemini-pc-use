"""Entry point for the Gemini desktop agent.

Run a task directly:
    py -3.13 main.py "open Notepad and type a short poem"

Or start the graphical interface:
    py -3.13 main.py
    py -3.13 main.py --gui
"""

from __future__ import annotations

import argparse
import logging
import sys

from agent import run_agent
from config import DEFAULT_MODEL
from logging_config import setup_logger


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description=(
            "Control your desktop with a Gemini vision agent, from the command "
            "line or from the graphical interface."
        ),
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        help=(
            "The high-level goal the agent should achieve. When omitted, the "
            "graphical interface starts instead."
        ),
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Force the graphical interface to start.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help=f"Gemini model to use (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Gemini API key. Prefer the GUI or the GEMINI_API_KEY variable.",
    )
    parser.add_argument(
        "--instant-click",
        dest="instant_click",
        action="store_true",
        default=None,
        help="Click immediately at the target point instead of animating the pointer.",
    )
    parser.add_argument(
        "--no-instant-click",
        dest="instant_click",
        action="store_false",
        help="Animate the pointer before clicking (overrides the saved setting).",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=None,
        help="Maximum number of agent steps before stopping.",
    )
    parser.add_argument(
        "--step-delay",
        type=float,
        default=None,
        help="Seconds to wait after each action (default: 0.1).",
    )
    parser.add_argument(
        "--debug-screenshots",
        action="store_true",
        default=None,
        help="Save every screenshot as debug_screenshot.png.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.gui or not args.prompt:
        try:
            from frontend.app import launch_gui
        except ImportError as error:
            print(
                "The graphical interface needs PyQt6. Install it with:\n"
                "    py -3.13 -m pip install PyQt6\n"
                f"Details: {error}",
                file=sys.stderr,
            )
            return 1
        return launch_gui(
            initial_prompt=args.prompt or "",
            initial_model=args.model,
            initial_instant_click=args.instant_click,
        )

    setup_logger(logging.DEBUG if args.verbose else logging.INFO)
    logging.info("Starting the agent with the goal: '%s'", args.prompt)
    success = run_agent(
        args.prompt,
        api_key=args.api_key,
        model=args.model,
        instant_click=args.instant_click,
        max_steps=args.max_steps,
        step_delay=args.step_delay,
        save_screenshots=args.debug_screenshots,
    )
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
