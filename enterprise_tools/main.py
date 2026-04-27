"""
main.py - Entry point for Enterprise Tools Suite
"""
import os
import sys
import ctypes

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from ui.dashboard import DashboardWindow
from utils.logger import setup_logging, log_unhandled_exception
from database.db import init_db
from utils.app_paths import get_app_home


def _resolve_app_icon_path() -> str:
    candidate_rel_paths = [
        os.path.join("assets", "iconoavis.ico"),
        os.path.join("assets", "iconoaavis.ico"),
        os.path.join("assets", "app_icon.ico"),
        os.path.join("assets", "app_icon.png"),
        os.path.join("assets", "avista_logo.png"),
    ]

    if getattr(sys, "frozen", False):
        base_paths = [
            getattr(sys, "_MEIPASS", ""),
            os.path.dirname(sys.executable),
        ]
    else:
        app_root = os.path.dirname(__file__)
        workspace_root = os.path.dirname(app_root)
        base_paths = [app_root, workspace_root]

    for base_path in base_paths:
        if not base_path:
            continue

        for relative_path in candidate_rel_paths:
            direct_path = os.path.join(base_path, relative_path)
            if os.path.isfile(direct_path):
                return direct_path

            nested_path = os.path.join(base_path, "enterprise_tools", relative_path)
            if os.path.isfile(nested_path):
                return nested_path

    return ""


def _set_windows_app_id() -> None:
    if os.name != "nt":
        return

    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("avista.tools.enterprise")
    except Exception:
        pass


def main():
    app_home = get_app_home()
    os.environ["ENTERPRISE_TOOLS_HOME"] = app_home
    setup_logging()
    sys.excepthook = log_unhandled_exception
    init_db()
    _set_windows_app_id()
    app = QApplication(sys.argv)
    app.styleHints().setColorScheme(Qt.ColorScheme.Light)
    icon_path = _resolve_app_icon_path()
    icon = QIcon(icon_path) if icon_path else QIcon()
    if not icon.isNull():
        app.setWindowIcon(icon)

    window = DashboardWindow()
    if not icon.isNull():
        window.setWindowIcon(icon)

    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
