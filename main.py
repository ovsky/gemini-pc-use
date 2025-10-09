import argparse
import logging
from agent import run_agent
from logging_config import setup_logger

def main():
    """
    Der Haupteinstiegspunkt des Programms.
    Initialisiert das Logging, parst die Kommandozeilen-Argumente und startet den Agenten.
    """
    setup_logger()
    
    parser = argparse.ArgumentParser(description="Führt eine komplexe Aufgabe auf dem Desktop mit einem KI-Agenten aus.")
    parser.add_argument("prompt", type=str, help="Das übergeordnete Ziel, das der Agent erreichen soll.")
    args = parser.parse_args()
    
    logging.info(f"Agent wird mit dem Ziel gestartet: '{args.prompt}'")
    run_agent(args.prompt)

if __name__ == "__main__":
    main()
