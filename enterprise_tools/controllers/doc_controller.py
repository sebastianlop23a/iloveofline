"""
doc_controller.py - Controller for document conversion tools
"""
import os
from services.doc_service import DocService
from services.background_executor import submit_conversion
from database.db import get_connection
from utils.logger import logging, log_history_action
import datetime

class DocController:
    def convert(self, input_path, output_path):
        """Encola la conversión en segundo plano para no bloquear la UI.

        La finalización actualiza el historial en la base de datos cuando termina.
        """
        # Determinar operación según extensión
        ext = os.path.splitext(input_path)[1].lower()
        raise ValueError(
            "La conversión de Word, Excel y PowerPoint a PDF ya no está disponible."
        )

    def _log_action(self, action, file_name):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO history (action, file_name, timestamp) VALUES (?, ?, ?)",
            (action, file_name, datetime.datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
        log_history_action(action, file_name)
