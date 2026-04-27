#!/usr/bin/env python3
import subprocess
import os
import sys
import shutil

# Cambiar al directorio del proyecto
project_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(project_dir)

print("Limpiando directorios de compilación...")

# Limpiar carpetas
for folder in ["build", "dist", "enterprise_tools/dist"]:
    if os.path.exists(folder):
        try:
            shutil.rmtree(folder)
            print(f"✅ Eliminada carpeta: {folder}")
        except Exception as e:
            print(f"⚠️  Error eliminando {folder}: {e}")

print("\nCompilando aplicación...")
print("Directorio:", os.getcwd())

# Ejecutar PyInstaller sin --clean
resultado = subprocess.run([
    sys.executable, "-m", "PyInstaller",
    "enterprise_tools/main.spec",
    "--distpath", "version final"
])

if resultado.returncode == 0:
    print("\n✅ Compilación completada exitosamente")
    exe_path = os.path.join(project_dir, "version final", "main.exe")
    if os.path.exists(exe_path):
        print(f"✅ Ejecutable listo en: {exe_path}")
else:
    print(f"\n❌ Error en la compilación. Código: {resultado.returncode}")

sys.exit(resultado.returncode)
