import logging
import sys
from datetime import datetime

def setup_logger():
    """
    Konfiguriert das zentrale Logging für die Anwendung.
    Alle Ausgaben werden in 'computer-use.log' und auf der Konsole ausgegeben.
    """
    log_filename = 'computer-use.log'
    
    # Erstelle einen Formatter, der Zeitstempel und Loglevel enthält
    log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Root-Logger holen
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO) # Niedrigstes Loglevel, das verarbeitet wird

    # File Handler: Schreibt Logs in die Datei im 'write'-Modus (überschreiben)
    file_handler = logging.FileHandler(log_filename, mode='w')
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)

    # Stream Handler: Schreibt Logs in die Konsole (stdout)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(log_formatter)
    root_logger.addHandler(stream_handler)

    # Separator für den Start eines neuen Laufs
    root_logger.info("\n\n" + "="*30 + f" NEUER LAUF GESTARTET: {datetime.now()} " + "="*30)

