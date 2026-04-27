"""
zip_view.py - UI profesional para módulo de descompresión ZIP
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog,
    QLineEdit, QHBoxLayout, QMessageBox, QProgressBar,
    QFrame, QGraphicsDropShadowEffect
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt
from controllers.zip_controller import ZipController
from utils.app_paths import get_output_dir
from utils.drag_drop import extract_dropped_paths, filter_existing_directories, filter_existing_files
import os


class ZipView(QWidget):
    def __init__(self):
        super().__init__()
        self.controller = ZipController()
        self.default_output_dir = get_output_dir("zip")
        self._init_ui()

    def _init_ui(self):
        self.setAcceptDrops(True)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(60, 40, 60, 40)
        main_layout.setSpacing(30)

        # ===== CARD PRINCIPAL =====
        self.card = QFrame()
        self.card.setObjectName("MainCard")
        card_layout = QVBoxLayout()
        card_layout.setSpacing(25)
        card_layout.setContentsMargins(40, 40, 40, 40)

        # ===== TÍTULO =====
        self.title = QLabel("Descompresión ZIP")
        self.title.setObjectName("Title")

        self.subtitle = QLabel("Extrae archivos comprimidos fácilmente y de forma segura.")
        self.subtitle.setObjectName("Subtitle")

        # ===== INPUT ZIP =====
        self.file_input = QLineEdit()
        self.file_input.setPlaceholderText("Selecciona un archivo ZIP...")

        self.btn_browse = QPushButton("Buscar ZIP")
        self.btn_browse.clicked.connect(self._select_zip)

        file_layout = QHBoxLayout()
        file_layout.setSpacing(15)
        file_layout.addWidget(self.file_input)
        file_layout.addWidget(self.btn_browse)

        # ===== INPUT DESTINO =====
        self.dest_input = QLineEdit()
        self.dest_input.setPlaceholderText("Carpeta destino (se guarda dentro de la app)...")
        self.dest_input.setText(self.default_output_dir)

        self.btn_dest = QPushButton("Buscar carpeta")
        self.btn_dest.clicked.connect(self._select_dest)

        dest_layout = QHBoxLayout()
        dest_layout.setSpacing(15)
        dest_layout.addWidget(self.dest_input)
        dest_layout.addWidget(self.btn_dest)

        # ===== BOTÓN EXTRAER =====
        self.btn_extract = QPushButton("Extraer archivo")
        self.btn_extract.setObjectName("PrimaryButton")
        self.btn_extract.setFixedHeight(45)
        self.btn_extract.clicked.connect(self._extract_zip)

        # ===== PROGRESS BAR =====
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setFixedHeight(12)
        self.progress.setTextVisible(False)

        # ===== AGREGAR TODO AL CARD =====
        card_layout.addWidget(self.title)
        card_layout.addWidget(self.subtitle)
        card_layout.addSpacing(10)
        card_layout.addLayout(file_layout)
        card_layout.addLayout(dest_layout)
        card_layout.addSpacing(10)
        card_layout.addWidget(self.btn_extract)
        card_layout.addWidget(self.progress)

        self.card.setLayout(card_layout)

        # ===== SOMBRA =====
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 40))
        self.card.setGraphicsEffect(shadow)

        main_layout.addWidget(self.card)
        main_layout.addStretch()

        self.setLayout(main_layout)

    def dragEnterEvent(self, event):
        dropped_paths = extract_dropped_paths(event.mimeData())
        dropped_zips = filter_existing_files(dropped_paths, allowed_extensions=(".zip",))
        dropped_dirs = filter_existing_directories(dropped_paths)
        if dropped_zips or dropped_dirs:
            event.acceptProposedAction()
            return
        event.ignore()

    def dropEvent(self, event):
        dropped_paths = extract_dropped_paths(event.mimeData())
        dropped_zips = filter_existing_files(dropped_paths, allowed_extensions=(".zip",))
        dropped_dirs = filter_existing_directories(dropped_paths)

        accepted = False

        if dropped_zips:
            self.file_input.setText(os.path.abspath(dropped_zips[0]))
            accepted = True

        if dropped_dirs:
            self.dest_input.setText(os.path.abspath(dropped_dirs[0]))
            accepted = True

        if accepted:
            event.acceptProposedAction()
            return

        event.ignore()

    # ===============================
    # FUNCIONES
    # ===============================

    def _select_zip(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar ZIP", "", "Archivos ZIP (*.zip)"
        )
        if file_path:
            self.file_input.setText(file_path)

    def _select_dest(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Seleccionar carpeta destino", self.default_output_dir
        )
        if folder:
            normalized = os.path.abspath(folder)
            app_zip = os.path.abspath(self.default_output_dir)
            if not os.path.normcase(normalized).startswith(os.path.normcase(app_zip)):
                normalized = os.path.join(app_zip, os.path.basename(normalized))
                os.makedirs(normalized, exist_ok=True)
            self.dest_input.setText(normalized)

    def _extract_zip(self):
        zip_path = self.file_input.text()
        dest_folder = self.dest_input.text()

        if not zip_path or not os.path.isfile(zip_path):
            QMessageBox.warning(self, "Error", "Selecciona un archivo ZIP válido.")
            return

        if not dest_folder:
            zip_name = os.path.splitext(os.path.basename(zip_path))[0]
            dest_folder = os.path.join(self.default_output_dir, zip_name)
            self.dest_input.setText(dest_folder)

        app_zip = os.path.abspath(self.default_output_dir)
        normalized_dest = os.path.abspath(dest_folder)
        if not os.path.normcase(normalized_dest).startswith(os.path.normcase(app_zip)):
            normalized_dest = os.path.join(app_zip, os.path.basename(normalized_dest))
            self.dest_input.setText(normalized_dest)

        os.makedirs(normalized_dest, exist_ok=True)

        self.progress.setValue(20)

        try:
            self.controller.extract_zip(zip_path, normalized_dest)
            self.progress.setValue(100)
            QMessageBox.information(self, "Éxito", f"Archivo extraído en:\n{normalized_dest}")
        except Exception as e:
            self.progress.setValue(0)
            QMessageBox.critical(self, "Error", f"No se pudo extraer el archivo: {e}")
