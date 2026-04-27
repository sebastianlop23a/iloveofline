#!/usr/bin/env python3
"""
Script para hacer las carpetas de logs ocultas
"""
import os
import ctypes

def make_hidden(path):
    """Hace una carpeta oculta en Windows"""
    try:
        FILE_ATTRIBUTE_HIDDEN = 0x02
        ctypes.windll.kernel32.SetFileAttributesW(str(path), FILE_ATTRIBUTE_HIDDEN)
        print(f"Carpeta oculta: {path}")
    except Exception as e:
        print(f"No se pudo ocultar {path}: {e}")

if __name__ == "__main__":
    # Hacer ocultas las carpetas de logs existentes
    logs_paths = [
        os.path.join(os.getcwd(), "logs"),
        os.path.join(os.getcwd(), "enterprise_tools", "logs")
    ]

    for path in logs_paths:
        if os.path.exists(path):
            make_hidden(path)