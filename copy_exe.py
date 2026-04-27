#!/usr/bin/env python3
import shutil
import os

origen = r"c:\Users\SebastianLopez\OneDrive - AVISTA COLOMBIA SAS\Escritorio\ti herramientas\dist_release_20260406_160932\main.exe"
destino = r"c:\Users\SebastianLopez\OneDrive - AVISTA COLOMBIA SAS\Escritorio\ti herramientas\version final\main.exe"

if os.path.exists(origen):
    shutil.copy2(origen, destino)
    print(f"Copiado: {origen}")
    print(f"A: {destino}")
else:
    print(f"No existe: {origen}")
