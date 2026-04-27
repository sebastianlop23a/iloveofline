"""
images_to_pdf_view.py - Vista para convertir imágenes a PDF
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QListWidget, QMessageBox, QProgressBar
from controllers.pdf_controller import PDFController
from utils.app_paths import get_output_dir, ensure_in_output_dir
from utils.drag_drop import extract_dropped_paths, filter_existing_files
import os

class ImagesToPDFView(QWidget):
    def __init__(self):
        super().__init__()
        self.controller = PDFController()
        self.image_files = []
        self._init_ui()

    def _init_ui(self):
        self.setAcceptDrops(True)
        layout = QVBoxLayout()
        self.label = QLabel("Convertir imágenes a PDF")
        self.btn_select = QPushButton("Seleccionar imágenes")
        self.btn_select.clicked.connect(self._select_images)
        self.list_widget = QListWidget()
        self.btn_convert = QPushButton("Convertir a PDF")
        self.btn_convert.clicked.connect(self._convert)
        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.label)
        layout.addWidget(self.btn_select)
        layout.addWidget(self.list_widget)
        layout.addWidget(self.btn_convert)
        layout.addWidget(self.progress)
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
            self._set_images(dropped_images)
            event.acceptProposedAction()
            return
        event.ignore()

    def _set_images(self, files):
        unique_files = []
        for file in files:
            normalized = os.path.abspath(file)
            if normalized not in unique_files:
                unique_files.append(normalized)

        self.image_files = unique_files
        self.list_widget.clear()
        for file in unique_files:
            self.list_widget.addItem(os.path.basename(file))

    def _select_images(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Seleccionar imágenes", "", "Imágenes (*.png *.jpg *.jpeg *.bmp)")
        if files:
            self._set_images(files)

    def _convert(self):
        if not self.image_files:
            QMessageBox.warning(self, "Error", "Selecciona imágenes primero.")
            return
        default_dir = get_output_dir("pdf")
        default_name = os.path.join(default_dir, "imagenes_a_pdf.pdf")
        output_file, _ = QFileDialog.getSaveFileName(self, "Guardar PDF como", default_name, "Archivos PDF (*.pdf)")
        if not output_file:
            return
        if not output_file.lower().endswith('.pdf'):
            output_file += '.pdf'
        output_file = ensure_in_output_dir(output_file, "pdf")
        self.progress.setValue(10)
        try:
            self.controller.images_to_pdf(self.image_files, output_file)
            self.progress.setValue(100)
            QMessageBox.information(self, "Éxito", f"Imágenes convertidas a PDF:\n{output_file}")
        except Exception as e:
            self.progress.setValue(0)
            QMessageBox.critical(self, "Error", f"No se pudo convertir las imágenes: {e}")
