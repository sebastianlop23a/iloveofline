#!/usr/bin/env python3
"""
Script para compilar la aplicación con PyInstaller
"""

import subprocess
import sys
import os

def main():
    # Cambiar al directorio del script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # Comando para ejecutar pyinstaller
    cmd = [sys.executable, "-m", "pyinstaller", "--clean", "main.spec"]

    print(f"Ejecutando: {' '.join(cmd)}")
    print(f"Directorio: {script_dir}")

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Compilación exitosa!")
        print("STDOUT:", result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
    except subprocess.CalledProcessError as e:
        print(f"Error en compilación: {e}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()