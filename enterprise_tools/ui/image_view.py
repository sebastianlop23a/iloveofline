"""
image_view.py - UI para el módulo de imágenes
"""
import os
import sys

if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QProgressBar,
    QHBoxLayout,
    QLineEdit,
    QFrame,
    QGraphicsDropShadowEffect,
)
from PySide6.QtGui import QColor

from controllers.image_controller import ImageController
from utils.app_paths import get_output_dir
from utils.drag_drop import extract_dropped_paths, filter_existing_files

class ImageView(QWidget):
    def __init__(self):
        super().__init__()
        self.controller = ImageController()
        self.image_file = None
        self._init_ui()

    def _init_ui(self):
        self.setAcceptDrops(True)
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 18, 24, 18)
        layout.setSpacing(16)

        card = QFrame()
        card.setObjectName("MainCard")
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(28, 24, 28, 24)
        card_layout.setSpacing(14)

        self.title = QLabel("Comprimir imagen por límite de tamaño")
        self.title.setObjectName("Title")
        self.subtitle = QLabel("Ideal para sistemas que exigen máximo 100 KB")
        self.subtitle.setObjectName("Subtitle")

        self.btn_select = QPushButton("Seleccionar imagen")
        self.btn_select.clicked.connect(self._select_image)

        max_layout = QHBoxLayout()
        self.max_kb_input = QLineEdit("100")
        self.max_kb_input.setPlaceholderText("Máximo en KB")
        self.max_kb_input.setFixedWidth(120)
        self.btn_compress = QPushButton("Comprimir")
        self.btn_compress.clicked.connect(self._compress)
        max_layout.addWidget(QLabel("Máximo KB:"))
        max_layout.addWidget(self.max_kb_input)
        max_layout.addWidget(self.btn_compress)
        max_layout.addStretch()

        self.file_label = QLabel("Sin archivo seleccionado")
        self.progress = QProgressBar()
        self.progress.setValue(0)

        card_layout.addWidget(self.title)
        card_layout.addWidget(self.subtitle)
        card_layout.addWidget(self.btn_select)
        card_layout.addWidget(self.file_label)
        card_layout.addLayout(max_layout)
        card_layout.addWidget(self.progress)

        card.setLayout(card_layout)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 35))
        card.setGraphicsEffect(shadow)

        layout.addWidget(card)
        layout.addStretch()

        self.setLayout(layout)

    def dragEnterEvent(self, event):
        dropped_images = filter_existing_files(
            extract_dropped_paths(event.mimeData()),
            allowed_extensions=(".png", ".jpg", ".jpeg", ".bmp", ".webp"),
        )
        if dropped_images:
            event.acceptProposedAction()
            return
        event.ignore()

    def dropEvent(self, event):
        dropped_images = filter_existing_files(
            extract_dropped_paths(event.mimeData()),
            allowed_extensions=(".png", ".jpg", ".jpeg", ".bmp", ".webp"),
        )
        if dropped_images:
            self._set_image_file(dropped_images[0])
            event.acceptProposedAction()
            return
        event.ignore()

    def _set_image_file(self, file_path):
        self.image_file = file_path
        self.file_label.setText(f"Archivo: {os.path.basename(file_path)}")

    def _select_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar imagen",
            "",
            "Imágenes (*.png *.jpg *.jpeg *.bmp *.webp)",
        )
        if file_path:
            self._set_image_file(file_path)

    def _compress(self):
        if not self.image_file:
            QMessageBox.warning(self, "Error", "Selecciona una imagen primero.")
            return

        try:
            max_kb = int(self.max_kb_input.text().strip())
            if max_kb <= 0:
                raise ValueError()
        except Exception:
            QMessageBox.warning(self, "Error", "Ingresa un valor de KB válido.")
            return

        output_dir = get_output_dir("imagenes")
        base_name = os.path.splitext(os.path.basename(self.image_file))[0]
        output_path = os.path.join(output_dir, f"{base_name}_{max_kb}kb.jpg")

        self.progress.setValue(15)
        try:
            _, final_kb = self.controller.compress_to_max_kb(self.image_file, output_path, max_kb=max_kb)
            self.progress.setValue(100)
            if final_kb <= max_kb:
                QMessageBox.information(
                    self,
                    "Éxito",
                    f"Imagen comprimida correctamente.\nTamaño final: {final_kb} KB\nGuardada en:\n{output_path}",
                )
            else:
                QMessageBox.information(
                    self,
                    "Resultado parcial",
                    f"No fue posible llegar a {max_kb} KB exactos.\nMejor resultado: {final_kb} KB\nGuardada en:\n{output_path}",
                )
        except Exception as e:
            self.progress.setValue(0)
            QMessageBox.critical(self, "Error", f"No se pudo comprimir la imagen: {e}")
