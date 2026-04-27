"""
zip_controller.py - Controller for ZIP extraction UI actions
"""
from services.zip_service import ZipService
from database.db import get_connection
from utils.logger import logging, log_history_action
import datetime

class ZipController:
    def extract_zip(self, file_path, dest_folder):
        try:
            ZipService.extract_zip(file_path, dest_folder)
            self._log_action('extract_zip', dest_folder)
        except Exception as e:
            logging.error(f"Error extrayendo ZIP: {e}")
            raise

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
