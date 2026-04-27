"""
image_controller.py - Controller for image tools
"""
from services.image_service import ImageService
from database.db import get_connection
from utils.logger import logging, log_history_action
import datetime

class ImageController:
    def convert(self, input_path, output_path, format):
        try:
            ImageService.convert_image(input_path, output_path, format)
            self._log_action('convert_image', output_path)
        except Exception as e:
            logging.error(f"Error convirtiendo imagen: {e}")
            raise

    def resize(self, input_path, output_path, size):
        try:
            ImageService.resize_image(input_path, output_path, size)
            self._log_action('resize_image', output_path)
        except Exception as e:
            logging.error(f"Error redimensionando imagen: {e}")
            raise

    def compress(self, input_path, output_path, quality=70):
        try:
            ImageService.compress_image(input_path, output_path, quality)
            self._log_action('compress_image', output_path)
        except Exception as e:
            logging.error(f"Error comprimiendo imagen: {e}")
            raise

    def compress_to_max_kb(self, input_path, output_path, max_kb=100):
        try:
            result_path, final_kb = ImageService.compress_image_to_max_kb(input_path, output_path, max_kb=max_kb)
            self._log_action('compress_image_max_kb', result_path)
            return result_path, final_kb
        except Exception as e:
            logging.error(f"Error comprimiendo imagen a tamaño objetivo: {e}")
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
