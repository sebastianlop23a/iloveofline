#!/usr/bin/env python3
"""
Script para verificar si LibreOffice está instalado y configurar la conversión.
"""
import os
import shutil
import subprocess

def check_soffice():
    soffice_path = shutil.which("soffice")
    if soffice_path:
        print(f"✅ LibreOffice encontrado en: {soffice_path}")
        return True

    # Buscar en rutas comunes
    common_paths = [
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        r"C:\LibreOffice\program\soffice.exe",
    ]

    for path in common_paths:
        if os.path.exists(path):
            print(f"✅ LibreOffice encontrado en: {path}")
            print("Agrega esta ruta al PATH del sistema o define SOFFICE_PATH en variables de entorno.")
            return True

    print("❌ LibreOffice no encontrado.")
    print("Descarga e instala LibreOffice desde: https://www.libreoffice.org/download/download/")
    return False

if __name__ == "__main__":
    check_soffice()