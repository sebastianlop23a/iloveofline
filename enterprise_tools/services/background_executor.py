"""
background_executor.py - Ejecuta tareas de conversión en segundo plano

Proporciona un wrapper simple sobre ThreadPoolExecutor para ejecutar
`execute_conversion` sin bloquear la UI. Acepta callbacks de progreso
y finalización (serán invocados desde el hilo trabajador).

Nota: Si la UI es PySide6, los callbacks de finalización deben reenviarse
al hilo principal si actualizan widgets (usar señales/Qt.invokeLater).
"""
from __future__ import annotations

import os
import traceback
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Callable, Optional

from services.conversion_service import execute_conversion

# Crear executor con N-1 workers por defecto (no saturar el equipo)
_WORKERS = max(1, (os.cpu_count() or 2) - 1)
_EXECUTOR: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=_WORKERS)


def _worker_wrapper(operation_key: str, input_source, output_target: str, progress_callback: Optional[Callable] = None):
    """Wrapper que ejecuta la conversión y permite llamadas de progreso.

    `progress_callback(percent:int, message:str)` puede ser llamado desde
    la implementación si está soportado; aquí no hay hooks internos, pero
    lo mantenemos para compatibilidad con funciones que acepten callbacks.
    """
    try:
        # execute_conversion es síncrono; lo llamamos directamente
        result = execute_conversion(operation_key, input_source, output_target)
        return (True, result)
    except Exception as exc:
        return (False, f"{exc}\n{traceback.format_exc()}")


def submit_conversion(operation_key: str, input_source, output_target: str, *,
                      progress_callback: Optional[Callable[[int, str], None]] = None,
                      done_callback: Optional[Callable[[bool, str], None]] = None) -> Future:
    """Encola una conversión para ejecutarse en segundo plano.

    - `progress_callback(percent, message)` será invocado desde el hilo worker
      sólo si la tarea llama explícitamente a ese callback (algunas funciones
      de conversión lo soportan mediante parámetros; la implementación actual
      no inyecta el callback dentro de `execute_conversion`).
    - `done_callback(success: bool, result_or_error: str)` se invoca cuando la
      tarea termina (desde el hilo worker). Si la UI necesita manipular widgets,
      reexpón la llamada al hilo principal (Qt). 

    Devuelve un `Future` para seguimiento adicional.
    """

    future: Future = _EXECUTOR.submit(_worker_wrapper, operation_key, input_source, output_target, progress_callback)

    if done_callback:
        def _on_done(f: Future):
            try:
                ok, payload = f.result()
            except Exception as exc:
                ok = False
                payload = f"{exc}\n{traceback.format_exc()}"
            try:
                done_callback(ok, payload)
            except Exception:
                # Evitar que excepciones en el callback cancelen el worker
                pass

        future.add_done_callback(_on_done)

    return future
