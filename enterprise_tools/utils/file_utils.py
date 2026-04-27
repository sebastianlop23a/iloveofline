"""
file_utils.py - File import/export and safe operations
"""
import os
import shutil
from utils.logger import logging

def import_file(src, dest_dir):
    try:
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        dest = os.path.join(dest_dir, os.path.basename(src))
        shutil.copy2(src, dest)
        logging.info(f"Archivo importado: {dest}")
        return dest
    except Exception as e:
        logging.error(f"Error importando archivo: {e}")
        raise

def export_file(src, dest_dir):
    try:
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        dest = os.path.join(dest_dir, os.path.basename(src))
        shutil.copy2(src, dest)
        logging.info(f"Archivo exportado: {dest}")
        return dest
    except Exception as e:
        logging.error(f"Error exportando archivo: {e}")
        raise
