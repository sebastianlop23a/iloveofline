"""
doc_service.py - Document conversion service (basic)
"""
import os
from utils.logger import logging

class DocService:
    @staticmethod
    def convert_doc(input_path, output_path):
        # Placeholder: Implement conversion logic using e.g. docx2pdf, unoconv, etc.
        logging.info(f"Conversión de documento: {input_path} → {output_path}")
        # Raise NotImplementedError for now
        raise NotImplementedError("Conversión de documentos aún no implementada.")
