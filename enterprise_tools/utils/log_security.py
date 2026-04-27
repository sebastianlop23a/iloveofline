import base64
import hashlib
import hmac
import json
import os

from PySide6.QtWidgets import QInputDialog, QLineEdit, QMessageBox

from utils.app_paths import get_app_home
from utils.logger import get_logs_dir


_AUTH_FILE_NAME = ".logs_access.json"
_PBKDF2_ITERATIONS = 180000


def _auth_file_path() -> str:
    return os.path.join(get_app_home(), _AUTH_FILE_NAME)


def _hash_password(password: str, salt: bytes, iterations: int) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)


def _save_password(password: str):
    salt = os.urandom(16)
    digest = _hash_password(password, salt, _PBKDF2_ITERATIONS)

    payload = {
        "salt": base64.b64encode(salt).decode("utf-8"),
        "hash": base64.b64encode(digest).decode("utf-8"),
        "iterations": _PBKDF2_ITERATIONS,
    }

    with open(_auth_file_path(), "w", encoding="utf-8") as file:
        json.dump(payload, file)


def _load_password_data():
    path = _auth_file_path()
    if not os.path.isfile(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as file:
            payload = json.load(file)

        salt = base64.b64decode(payload["salt"])
        digest = base64.b64decode(payload["hash"])
        iterations = int(payload.get("iterations", _PBKDF2_ITERATIONS))

        if not salt or not digest or iterations <= 0:
            return None

        return salt, digest, iterations
    except Exception:
        return None


def _ask_password(parent, title: str, prompt: str):
    password, ok = QInputDialog.getText(parent, title, prompt, QLineEdit.Password)
    if not ok:
        return None
    return password


def _configure_password(parent) -> bool:
    password_1 = _ask_password(parent, "Configurar contraseña", "Define la contraseña para abrir logs:")
    if password_1 is None:
        return False

    if len(password_1) < 4:
        QMessageBox.warning(parent, "Contraseña inválida", "La contraseña debe tener al menos 4 caracteres.")
        return False

    password_2 = _ask_password(parent, "Confirmar contraseña", "Confirma la contraseña de logs:")
    if password_2 is None:
        return False

    if password_1 != password_2:
        QMessageBox.warning(parent, "No coincide", "Las contraseñas no coinciden.")
        return False

    _save_password(password_1)
    QMessageBox.information(parent, "Configuración lista", "Contraseña de logs configurada correctamente.")
    return True


def _verify_password(candidate: str, password_data) -> bool:
    if candidate is None:
        return False

    salt, expected_digest, iterations = password_data
    candidate_digest = _hash_password(candidate, salt, iterations)
    return hmac.compare_digest(candidate_digest, expected_digest)


def request_logs_access(parent):
    logs_dir = get_logs_dir()
    password_data = _load_password_data()

    if password_data is None:
        QMessageBox.information(
            parent,
            "Protección de logs",
            "Primero debes configurar una contraseña para proteger la carpeta de logs.",
        )
        if not _configure_password(parent):
            return None
        return logs_dir

    attempts = 3
    for attempt in range(attempts):
        candidate = _ask_password(parent, "Acceso a logs", "Ingresa tu contraseña para abrir la carpeta de logs:")
        if candidate is None:
            return None

        if _verify_password(candidate, password_data):
            return logs_dir

        remaining = attempts - attempt - 1
        if remaining > 0:
            QMessageBox.warning(parent, "Contraseña incorrecta", f"Contraseña incorrecta. Intentos restantes: {remaining}")

    QMessageBox.critical(parent, "Acceso denegado", "No fue posible validar la contraseña de logs.")
    return None
