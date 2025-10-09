import pyautogui
import time

# Deaktiviere die Fail-Safe-Funktion von pyautogui, um Mausbewegungen in die Ecken zu ermöglichen.
# HINWEIS: Dies sollte mit Vorsicht verwendet werden.
pyautogui.FAILSAFE = False

class DesktopComputer:
    """
    Eine Schnittstelle zur Steuerung des Desktops, die dem Gemini-Modell als Werkzeug zur Verfügung gestellt wird.
    Diese Klasse kapselt alle Aktionen, die mit pyautogui ausgeführt werden.
    """
    def __init__(self):
        self.is_done = False

    def click_at(self, x: int, y: int):
        """
        Bewegt die Maus an die angegebene normalisierte Koordinate (0-1000) und führt einen einzelnen Klick aus.
        """
        screen_width, screen_height = pyautogui.size()
        pixel_x = int((x / 1000) * screen_width)
        pixel_y = int((y / 1000) * screen_height)
        
        print(f"Aktion: Klick bei ({pixel_x}, {pixel_y})")
        pyautogui.moveTo(pixel_x, pixel_y, duration=1.0, tween=pyautogui.easeInOutQuad)
        pyautogui.click()

    def double_click_at(self, x: int, y: int):
        """
        Bewegt die Maus an die angegebene normalisierte Koordinate (0-1000) und führt einen Doppelklick aus.
        """
        screen_width, screen_height = pyautogui.size()
        pixel_x = int((x / 1000) * screen_width)
        pixel_y = int((y / 1000) * screen_height)

        print(f"Aktion: Doppelklick bei ({pixel_x}, {pixel_y})")
        pyautogui.moveTo(pixel_x, pixel_y, duration=1.0, tween=pyautogui.easeInOutQuad)
        pyautogui.doubleClick()

    def type_text(self, text: str):
        """Tippt den angegebenen Text an der aktuellen Mausposition."""
        print(f"Aktion: Tippe '{text}'")
        pyautogui.write(text, interval=0.05)

    def press_key(self, key: str):
        """Drückt eine spezielle Taste (z.B. 'enter', 'esc', 'win')."""
        print(f"Aktion: Drücke Taste '{key}'")
        pyautogui.press(key)

    def done(self):
        """
        Signalisiert, dass die Aufgabe abgeschlossen ist und der Agent stoppen kann.
        """
        print("Aktion: Aufgabe als erledigt markiert.")
        self.is_done = True
