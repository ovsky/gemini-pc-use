import os
import sys
import time
import io
import logging
import pyautogui
import google.genai as genai
from google.genai import types
from dotenv import load_dotenv

SYSTEM_PROMPT = """
Sie bedienen einen Windows 11 Desktop. Ihre Aufgabe ist es, das vom Benutzer angegebene Ziel zu erreichen, indem Sie eine Reihe von Aktionen über die bereitgestellten Tools ausführen.

Wichtige Regeln:
- Koordinaten (x, y) sind normalisiert von 0 bis 1000 (0,0 ist oben links; 1000,1000 ist unten rechts).
- Um ein Icon auf dem Desktop (Ordner, Datei, Programm) zu öffnen, MÜSSEN Sie `double_click_at` verwenden.
- Um einen Button anzuklicken oder ein Element auszuwählen, verwenden Sie `click_at`.
- Um Programme schnell zu starten, können Sie `hotkey` mit ['Win', 'r'] verwenden.
- Wenn Sie Text eingeben müssen, verwenden Sie `type_text_at` (oder `type_text`, wenn das Eingabefeld bereits fokussiert ist).
- Bestätigen Sie Dialoge oder Eingaben mit `press_key` und der Taste 'enter'.
- Zusatzregel: Manche Buttons, besonders 'Weiter' oder 'Next', sehen möglicherweise deaktiviert (ausgegraut) aus, obwohl sie klickbar sind. Wenn 'Weiter' der logische nächste Schritt ist, versuche, darauf zu klicken.
- Wenn die Aufgabe vollständig erledigt ist, rufen Sie die Funktion `done` auf.
"""

def denormalize(val, max_val):
    return int((val / 1000) * max_val)

def normalize_key(k: str) -> str:
    key_map = {
        "win": "win",
        "windows": "win",
        "super": "win",
        "meta": "win",
        "control": "ctrl",
        "ctrl": "ctrl",
        "alt": "alt",
        "shift": "shift",
        "enter": "enter",
        "return": "enter",
        "escape": "esc",
        "esc": "esc",
        "backspace": "backspace",
        "tab": "tab",
        "space": "space",
    }
    return key_map.get(k.lower(), k.lower())

# Tool-Definitionen für Gemini
def click_at(x: int, y: int):
    """Klickt einmal mit der linken Maustaste an die normalisierten Koordinaten (0-1000)."""
    pass

def double_click_at(x: int, y: int):
    """Doppelklickt mit der linken Maustaste an die normalisierten Koordinaten (0-1000)."""
    pass

def type_text_at(x: int, y: int, text: str, press_enter: bool = False):
    """Klickt an (x, y) (0-1000), gibt den Text ein und drückt optional Enter."""
    pass

def type_text(text: str, press_enter: bool = False):
    """Gibt Text an der aktuellen Cursor-Position ein und drückt optional Enter."""
    pass

def press_key(key: str):
    """Drückt eine einzelne Taste (z.B. 'enter', 'tab', 'esc', 'win')."""
    pass

def hotkey(keys: list[str]):
    """Drückt eine Tastenkombination gleichzeitig (z.B. ['Win', 'r'] oder ['ctrl', 's'])."""
    pass

def done():
    """Rufen Sie diese Funktion auf, sobald das Ziel des Benutzers vollständig erreicht wurde."""
    pass

def run_agent(user_prompt: str):
    logger = logging.getLogger(__name__)

    load_dotenv()
    if not os.getenv("GEMINI_API_KEY"):
        logger.error("FEHLER: GEMINI_API_KEY nicht gefunden.")
        sys.exit(1)

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    models_to_try = ["gemini-3.5-flash-lite", "gemini-3.8-flash"]
#    models_to_try = ["gemini-3.8-flash", "gemini-3.8-flash"]
    model_index = 0
    model_name = models_to_try[model_index]

    generate_config = types.GenerateContentConfig(
        temperature=0.2,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        tools=[click_at, double_click_at, type_text_at, type_text, press_key, hotkey, done],
    )

    screen_width, screen_height = pyautogui.size()
    is_done = False
    action_history = []

    while not is_done:
        logger.info("--- Nächster Schritt ---")

        logger.info("Mache einen Screenshot...")
        screenshot = pyautogui.screenshot()
        screenshot.save("debug_screenshot.png")

        small_screenshot = screenshot.resize((1280, 720))
        byte_io = io.BytesIO()
        small_screenshot.save(byte_io, "JPEG", quality=80)
        screenshot_bytes = byte_io.getvalue()
        screenshot_part = types.Part(
            inline_data=types.Blob(mime_type="image/jpeg", data=screenshot_bytes)
        )

        history_prompt = (
            "Bisherige Aktionen:\n" + "\n".join(action_history)
            if action_history
            else "Dies ist der erste Schritt."
        )

        logger.info(f"Sende Anfrage an Gemini ({model_name})...")
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[
                    SYSTEM_PROMPT,
                    user_prompt,
                    history_prompt,
                    "Führe den nächsten logischen Schritt aus.",
                    screenshot_part,
                ],
                config=generate_config,
            )

            function_call = None
            if response.function_calls:
                function_call = response.function_calls[0]

            if not function_call:
                logger.error(f"Modell hat keine gültige Aktion zurückgegeben. Antwort: {response.text}")
                time.sleep(2)
                continue

        except Exception as e:
            logger.error(f"Fehler bei der Gemini-Anfrage: {e}")
            if "503" in str(e) and len(models_to_try) > 1:
                model_index = (model_index + 1) % len(models_to_try)
                model_name = models_to_try[model_index]
                logger.info(f"Wechsle zu Fallback-Modell: {model_name}")
            time.sleep(2)
            continue

        action_name = function_call.name
        action_args = dict(function_call.args) if function_call.args else {}
        logger.info(f"Modell schlägt vor: {action_name} mit Argumenten: {action_args}")

        if action_name == "done":
            is_done = True
            logger.info("Aufgabe abgeschlossen.")
        elif action_name in ["click_at", "double_click_at", "move_mouse"]:
            x = denormalize(action_args["x"], screen_width)
            y = denormalize(action_args["y"], screen_height)
            pyautogui.moveTo(x, y, duration=0.5, tween=pyautogui.easeInOutQuad)
            if "double" in action_name:
                pyautogui.doubleClick()
            elif "click" in action_name:
                pyautogui.click()
        elif action_name in ["type_text_at", "type_text"]:
            if "x" in action_args and "y" in action_args:
                x = denormalize(action_args["x"], screen_width)
                y = denormalize(action_args["y"], screen_height)
                pyautogui.moveTo(x, y, duration=0.5)
                pyautogui.click()
            pyautogui.write(action_args.get("text", ""), interval=0.03)
            if action_args.get("press_enter"):
                pyautogui.press("enter")
        elif action_name == "press_key":
            key = normalize_key(action_args.get("key", ""))
            if key:
                pyautogui.press(key)
        elif action_name == "hotkey":
            raw_keys = action_args.get("keys", [])
            if isinstance(raw_keys, str):
                raw_keys = raw_keys.split("+")
            keys = [normalize_key(k.strip()) for k in raw_keys if k.strip()]
            if keys:
                pyautogui.hotkey(*keys)
        else:
            logger.warning(f"Unbekannte Aktion '{action_name}' wird ignoriert.")

        history_entry = f"- {action_name}({action_args})"
        action_history.append(history_entry)
        time.sleep(2)
