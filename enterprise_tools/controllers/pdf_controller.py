"""
pdf_controller.py - Controller for PDF tools
"""
from services.pdf_service import merge_pdfs
from database.db import get_connection
from utils.logger import logging, log_history_action
import datetime

class PDFController:
    def get_conversion_operations(self):
        from services.conversion_service import get_conversion_operations
        return get_conversion_operations()

    def execute_conversion(self, operation_key, input_path, output_target):
        from services.conversion_service import execute_conversion
        try:
            result_path = execute_conversion(operation_key, input_path, output_target)
            self._log_action(f'convert_{operation_key}', result_path)
            return result_path
        except Exception as e:
            logging.error(f"Error en conversión '{operation_key}': {e}")
            raise

    def decrypt_pdf(self, pdf_path, password, output_path):
        from services.pdf_service import decrypt_pdf
        try:
            decrypt_pdf(pdf_path, password, output_path)
            logging.info(f"PDF desencriptado guardado en: {output_path}")
        except Exception as e:
            logging.error(f"Error desencriptando PDF: {e}")
            raise

    def split_selected_pages(self, pdf_path, output_dir, page_indexes):
        from services.pdf_service import split_pdf_selected_pages
        try:
            split_pdf_selected_pages(pdf_path, output_dir, page_indexes)
            self._log_action('split_pdf_selected_pages', output_dir)
        except Exception as e:
            logging.error(f"Error dividiendo PDF: {e}")
            raise

    def pdf_to_images(self, pdf_path, output_dir):
        from services.pdf_service import pdf_to_images
        try:
            pdf_to_images(pdf_path, output_dir)
            self._log_action('pdf_to_images', output_dir)
        except Exception as e:
            logging.error(f"Error convirtiendo PDF a imágenes: {e}")
            raise

    def images_to_pdf(self, image_paths, output_path):
        from services.pdf_service import images_to_pdf
        try:
            images_to_pdf(image_paths, output_path)
            self._log_action('images_to_pdf', output_path)
        except Exception as e:
            logging.error(f"Error convirtiendo imágenes a PDF: {e}")
            raise

    def merge(self, pdf_list, output_path):
        try:
            merge_pdfs(pdf_list, output_path)
            self._log_action('merge_pdfs', output_path)
        except Exception as e:
            logging.error(f"Error uniendo PDFs: {e}")
            raise

    def compress_to_max_kb(self, pdf_path, output_path, max_kb=100, progress_callback=None):
        from services.pdf_service import compress_pdf_to_max_kb_with_progress
        try:
            result_path, final_kb = compress_pdf_to_max_kb_with_progress(
                pdf_path,
                output_path,
                max_kb=max_kb,
                progress_callback=progress_callback,
            )
            self._log_action('compress_pdf_max_kb', result_path)
            return result_path, final_kb
        except Exception as e:
            logging.error(f"Error comprimiendo PDF por tamaño máximo: {e}")
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
