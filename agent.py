import os
import sys
import time
import pyautogui
import google.genai as genai
import io
import logging
from google.genai import types
from dotenv import load_dotenv

# System-Prompt, der dem Modell die Regeln für die Desktop-Bedienung beibringt.
SYSTEM_PROMPT = """
Sie bedienen einen Windows 11 Desktop. Ihre Aufgabe ist es, das vom Benutzer angegebene Ziel zu erreichen, indem Sie eine Reihe von Aktionen ausführen.

Wichtige Regeln:
- Um ein Icon auf dem Desktop (Ordner, Datei, Programm) zu öffnen, MÜSSEN Sie die Aktion `double_click_at` verwenden.
- Um einen Button anzuklicken oder ein Element auszuwählen, verwenden Sie einen normalen `click_at`.
- Wenn Sie Text eingeben müssen, verwenden Sie `type_text_at`.
- Bestätigen Sie Dialoge oder Eingaben mit `press_key` und der Taste 'enter'.
- **Zusatzregel:** Manche Buttons, besonders 'Weiter' oder 'Next', sehen möglicherweise deaktiviert (ausgegraut) aus, obwohl sie klickbar sind. Wenn 'Weiter' der logische nächste Schritt ist, versuche, darauf zu klicken, auch wenn er deaktiviert erscheint.
- Wenn die Aufgabe erledigt ist, rufen Sie die Funktion `done` auf.
"""

def denormalize(val, max_val):
    """Wandelt eine normalisierte Koordinate (0-1000) in einen Pixelwert um."""
    return int((val / 1000) * max_val)

def run_agent(user_prompt: str):
    """
    Startet und verwaltet die Agenten-Schleife, um ein gegebenes Ziel zu erreichen.
    """
    logger = logging.getLogger(__name__)

    load_dotenv()
    if not os.getenv("GEMINI_API_KEY"):
        logger.error("FEHLER: GEMINI_API_KEY nicht gefunden.")
        sys.exit(1)
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    model_name = "gemini-2.5-computer-use-preview-10-2025"

    computer_use_tool = types.Tool(
        computer_use=types.ComputerUse(
            environment=types.Environment.ENVIRONMENT_BROWSER
        )
    )
    generate_config = types.GenerateContentConfig(tools=[computer_use_tool])
    
    screen_width, screen_height = pyautogui.size()
    is_done = False
    action_history = []

    while not is_done:
        logger.info("--- Nächster Schritt ---")
        
        logger.info("Mache einen Screenshot...")
        screenshot = pyautogui.screenshot()
        screenshot.save("debug_screenshot.png")
        
        byte_io = io.BytesIO()
        screenshot.save(byte_io, 'PNG')
        screenshot_bytes = byte_io.getvalue()
        screenshot_part = types.Part(inline_data=types.Blob(mime_type="image/png", data=screenshot_bytes))

        history_prompt = "Bisherige Aktionen:\n" + "\n".join(action_history) if action_history else "Dies ist der erste Schritt."

        logger.info("Sende Anfrage an Gemini...")
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[SYSTEM_PROMPT, user_prompt, history_prompt, "Führe den nächsten logischen Schritt aus.", screenshot_part],
                config=generate_config
            )
            function_call = response.candidates[0].content.parts[0].function_call
        except (IndexError, ValueError) as e:
            logger.error(f"Modell hat keine gültige Aktion zurückgegeben. {e}")
            time.sleep(2)
            continue

        action_name = function_call.name
        action_args = dict(function_call.args)
        logger.info(f"Modell schlägt vor: {action_name} mit Argumenten: {action_args}")

        # Aktionen ausführen
        if action_name == "done":
            is_done = True
            logger.info("Aufgabe abgeschlossen.")
        elif action_name in ["click_at", "double_click_at", "move_mouse"]:
            x = denormalize(action_args["x"], screen_width)
            y = denormalize(action_args["y"], screen_height)
            pyautogui.moveTo(x, y, duration=1.0, tween=pyautogui.easeInOutQuad)
            if "double" in action_name:
                pyautogui.doubleClick()
            elif "click" in action_name:
                pyautogui.click()
        elif action_name == "type_text_at":
            x = denormalize(action_args["x"], screen_width)
            y = denormalize(action_args["y"], screen_height)
            pyautogui.moveTo(x, y, duration=1.0)
            pyautogui.click()
            pyautogui.write(action_args["text"], interval=0.05)
        elif action_name == "press_key":
            pyautogui.press(action_args["key"])
        else:
            logger.warning(f"Unbekannte Aktion '{action_name}' wird ignoriert.")

        # Aktion zur Historie hinzufügen
        history_entry = f"- {action_name}({action_args})"
        action_history.append(history_entry)
        time.sleep(5) # Längere Pause, damit die UI sich aktualisieren kann
