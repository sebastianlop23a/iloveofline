"""
home_view.py - Vista de inicio con accesos rápidos
"""

import os

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QGridLayout,
    QPushButton,
    QHBoxLayout,
)

from utils.app_paths import get_app_home
from utils.log_security import request_logs_access


class HomeView(QWidget):
    module_requested = Signal(int)

    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(14)

        title = QLabel("Centro de mando")
        title.setObjectName("HomeTitle")

        subtitle = QLabel(
            "Accede rápido a las herramientas principales y organiza tu flujo de trabajo"
        )
        subtitle.setObjectName("HomeSubtitle")
        subtitle.setWordWrap(True)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)

        actions = [
            ("Descompresión ZIP", "Extrae paquetes y carpetas", 1),
            ("Herramientas PDF", "Unir, dividir, convertir y comprimir", 2),
            ("Compresión PDF/Imagen", "Ahora integrada en PDF", 2),
            ("Explorador de historial", "Ver archivos generados", 3),
            ("Guías de soporte", "Resolver casos frecuentes", 4),
            ("Administrador de tareas", "Monitorear y optimizar el equipo", 5),
            ("Volver a Inicio", "Vista general del sistema", 0),
        ]

        for position, (name, description, target_index) in enumerate(actions):
            button = QPushButton(f"{name}\n{description}")
            button.setObjectName("HomeActionCard")
            button.setCursor(Qt.PointingHandCursor)
            button.setMinimumHeight(92)
            button.clicked.connect(lambda _, idx=target_index: self.module_requested.emit(idx))
            row, column = divmod(position, 2)
            grid.addWidget(button, row, column)

        quick_actions_row = QHBoxLayout()
        quick_actions_row.setSpacing(10)

        open_home_button = QPushButton("Abrir carpeta de trabajo")
        open_home_button.setObjectName("HomeSecondaryButton")
        open_home_button.clicked.connect(self._open_app_home)

        open_logs_button = QPushButton("Abrir logs")
        open_logs_button.setObjectName("HomeSecondaryButton")
        open_logs_button.clicked.connect(self._open_logs)

        go_pdf_button = QPushButton("Ir directo a PDF")
        go_pdf_button.setObjectName("HomeSecondaryButton")
        go_pdf_button.clicked.connect(lambda: self.module_requested.emit(2))

        quick_actions_row.addWidget(open_home_button)
        quick_actions_row.addWidget(open_logs_button)
        quick_actions_row.addWidget(go_pdf_button)
        quick_actions_row.addStretch()

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(8)
        layout.addLayout(grid)
        layout.addSpacing(4)
        layout.addLayout(quick_actions_row)
        layout.addStretch()

        self.setLayout(layout)

    def _open_app_home(self):
        self._open_folder(get_app_home())

    def _open_logs(self):
        logs_path = request_logs_access(self)
        if not logs_path:
            return
        self._open_folder(logs_path)

    def _open_folder(self, folder: str):
        os.makedirs(folder, exist_ok=True)
        if hasattr(os, "startfile"):
            os.startfile(folder)
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
