"""
logger.py - Logging setup for Enterprise Tools Suite
"""
import logging
import os
from utils.app_paths import get_app_home


def get_logs_dir() -> str:
    logs_dir = os.path.join(get_app_home(), "logs")
    os.makedirs(logs_dir, exist_ok=True)

    # Hacer la carpeta oculta en Windows
    try:
        import ctypes
        FILE_ATTRIBUTE_HIDDEN = 0x02
        ctypes.windll.kernel32.SetFileAttributesW(str(logs_dir), FILE_ATTRIBUTE_HIDDEN)
    except Exception:
        # Si no se puede hacer oculta, continuar normalmente
        pass

    return logs_dir

def setup_logging():
    logs_dir = get_logs_dir()
    app_log_path = os.path.join(logs_dir, "app.log")
    history_log_path = os.path.join(logs_dir, "history.log")

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(app_log_path, encoding='utf-8'),
            logging.StreamHandler()
        ],
        force=True,
    )

    history_logger = logging.getLogger("user_history")
    history_logger.setLevel(logging.INFO)
    history_logger.propagate = False
    history_logger.handlers.clear()

    history_handler = logging.FileHandler(history_log_path, encoding="utf-8")
    history_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    history_logger.addHandler(history_handler)

    logging.info(f"Sistema de logs inicializado en: {logs_dir}")


def log_history_action(action, file_name):
    safe_action = action or "accion_desconocida"
    safe_file = file_name or "-"

    logging.getLogger("user_history").info(f"{safe_action} | {safe_file}")
    logging.info(f"Historial usuario: {safe_action} -> {safe_file}")


def log_unhandled_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        return

    logging.critical(
        "Error no controlado en la aplicación",
        exc_info=(exc_type, exc_value, exc_traceback),
    )
