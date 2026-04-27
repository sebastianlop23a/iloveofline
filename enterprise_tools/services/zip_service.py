"""
zip_service.py - ZIP extraction and validation service
"""
import zipfile
import os
from utils.logger import logging

class ZipService:
    @staticmethod
    def validate_zip(file_path):
        return zipfile.is_zipfile(file_path)

    @staticmethod
    def extract_zip(file_path, dest_folder):
        if not ZipService.validate_zip(file_path):
            logging.error(f"Archivo no válido: {file_path}")
            raise ValueError("El archivo no es un ZIP válido.")
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(dest_folder)
        logging.info(f"ZIP extraído en: {dest_folder}")
