"""
pdf_to_images_view.py - Vista para convertir PDF a imágenes
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QListWidget, QMessageBox, QProgressBar
from controllers.pdf_controller import PDFController
from utils.app_paths import get_output_dir
from utils.drag_drop import extract_dropped_paths, filter_existing_files
import os
from datetime import datetime

class PDFToImagesView(QWidget):
    def __init__(self):
        super().__init__()
        self.controller = PDFController()
        self.pdf_file = None
        self._init_ui()

    def _init_ui(self):
        self.setAcceptDrops(True)
        layout = QVBoxLayout()
        self.label = QLabel("Convertir PDF a imágenes")
        self.btn_select = QPushButton("Seleccionar PDF")
        self.btn_select.clicked.connect(self._select_pdf)
        self.btn_convert = QPushButton("Convertir a imágenes")
        self.btn_convert.clicked.connect(self._convert)
        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.label)
        layout.addWidget(self.btn_select)
        layout.addWidget(self.btn_convert)
        layout.addWidget(self.progress)
        self.setLayout(layout)

    def dragEnterEvent(self, event):
        dropped_pdfs = filter_existing_files(
            extract_dropped_paths(event.mimeData()),
            allowed_extensions=(".pdf",),
        )
        if dropped_pdfs:
            event.acceptProposedAction()
            return
        event.ignore()

    def dropEvent(self, event):
        dropped_pdfs = filter_existing_files(
            extract_dropped_paths(event.mimeData()),
            allowed_extensions=(".pdf",),
        )
        if dropped_pdfs:
            self._set_pdf_file(dropped_pdfs[0])
            event.acceptProposedAction()
            return
        event.ignore()

    def _set_pdf_file(self, file_path):
        self.pdf_file = file_path
        self.label.setText(f"PDF seleccionado: {os.path.basename(file_path)}")

    def _select_pdf(self):
        file, _ = QFileDialog.getOpenFileName(self, "Seleccionar PDF", "", "Archivos PDF (*.pdf)")
        if file:
            self._set_pdf_file(file)

    def _convert(self):
        if not self.pdf_file:
            QMessageBox.warning(self, "Error", "Selecciona un PDF primero.")
            return
        base_output = get_output_dir("imagenes")
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_name = os.path.splitext(os.path.basename(self.pdf_file))[0]
        output_dir = os.path.join(base_output, f"pdf_a_imagenes_{pdf_name}_{stamp}")
        os.makedirs(output_dir, exist_ok=True)
        self.progress.setValue(10)
        try:
            self.controller.pdf_to_images(self.pdf_file, output_dir)
            self.progress.setValue(100)
            QMessageBox.information(self, "Éxito", f"PDF convertido a imágenes en:\n{output_dir}")
        except Exception as e:
            self.progress.setValue(0)
            QMessageBox.critical(self, "Error", f"No se pudo convertir el PDF: {e}")
