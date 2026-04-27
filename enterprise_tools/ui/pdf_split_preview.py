"""
pdf_split_preview.py - Vista para dividir PDF en páginas o rangos
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QLineEdit, QMessageBox, QProgressBar, QHBoxLayout
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
from controllers.pdf_controller import PDFController
from utils.app_paths import get_output_dir
from utils.drag_drop import extract_dropped_paths, filter_existing_files
from utils.pdf_preview import get_first_page_pixmap
import os
from datetime import datetime

class PDFSplitPreview(QWidget):
    def __init__(self):
        super().__init__()
        self.controller = PDFController()
        self.pdf_file = None
        self.default_output_dir = get_output_dir("pdf")
        self._init_ui()

    def _init_ui(self):
        self.setAcceptDrops(True)
        layout = QVBoxLayout()
        self.label = QLabel("Dividir PDF en páginas o rangos")
        self.btn_select = QPushButton("Seleccionar PDF")
        self.btn_select.clicked.connect(self._select_pdf)
        self.file_label = QLabel("Archivo: (sin seleccionar)")
        self.load_status = QLabel()
        self.load_status.setWordWrap(True)
        self._set_load_status(False)
        self.preview_thumb = QLabel("Sin\nvista previa")
        self.preview_thumb.setAlignment(Qt.AlignCenter)
        self.preview_thumb.setFixedSize(160, 220)
        self.preview_thumb.setStyleSheet(
            "border: 1px solid #CBD5E1; border-radius: 8px; background-color: #F8FAFC; color: #64748B;"
        )
        self.preview_title = QLabel("(sin seleccionar)")
        self.preview_title.setAlignment(Qt.AlignCenter)
        self.preview_title.setWordWrap(True)

        self.output_edit = QLineEdit(self.default_output_dir)
        self.output_edit.setPlaceholderText("Carpeta de salida")
        self.btn_output = QPushButton("Seleccionar carpeta de salida")
        self.btn_output.clicked.connect(self._select_output_dir)

        self.pages_edit = QLineEdit()
        self.pages_edit.setPlaceholderText("Ej: 1,3,5-7 para páginas específicas")
        self.btn_split = QPushButton("Dividir PDF")
        self.btn_split.clicked.connect(self._split_pdf)
        self.progress = QProgressBar()
        self.progress.setValue(0)

        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_edit)
        output_layout.addWidget(self.btn_output)

        layout.addWidget(self.label)
        layout.addWidget(self.btn_select)
        layout.addWidget(self.file_label)
        layout.addWidget(self.load_status)
        layout.addWidget(self.preview_thumb, alignment=Qt.AlignCenter)
        layout.addWidget(self.preview_title)
        layout.addLayout(output_layout)
        layout.addWidget(self.pages_edit)
        layout.addWidget(self.btn_split)
        layout.addWidget(self.progress)
        self.setLayout(layout)

    def dragEnterEvent(self, event):
        dropped_files = filter_existing_files(
            extract_dropped_paths(event.mimeData()),
            allowed_extensions=(".pdf",),
        )
        if dropped_files:
            event.acceptProposedAction()
            return
        event.ignore()

    def dropEvent(self, event):
        dropped_files = filter_existing_files(
            extract_dropped_paths(event.mimeData()),
            allowed_extensions=(".pdf",),
        )
        if dropped_files:
            self._set_pdf_file(dropped_files[0])
            event.acceptProposedAction()
            return
        event.ignore()

    def _create_thumbnail_pixmap(self, file_path, size=(160, 220)):
        return get_first_page_pixmap(file_path, max_width=size[0], max_height=size[1])

    def _set_pdf_file(self, file_path):
        self.pdf_file = file_path
        file_name = os.path.basename(file_path)
        self.file_label.setText(f"Archivo: {file_name}")
        self._set_load_status(True, file_name)
        self._update_preview(file_path)

    def _update_preview(self, file_path):
        self.preview_title.setText(os.path.basename(file_path))
        pixmap = self._create_thumbnail_pixmap(file_path)
        if pixmap and not pixmap.isNull():
            self.preview_thumb.setStyleSheet(
                "border: 1px solid #CBD5E1; border-radius: 8px; background-color: #FFFFFF;"
            )
            self.preview_thumb.setText("")
            self.preview_thumb.setPixmap(
                pixmap.scaled(152, 212, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        else:
            self.preview_thumb.setPixmap(QPixmap())
            self.preview_thumb.setText("Sin\nvista previa")
            self.preview_thumb.setStyleSheet(
                "border: 1px solid #CBD5E1; border-radius: 8px; background-color: #F8FAFC; color: #64748B;"
            )

    def _select_output_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta de salida", self.output_edit.text().strip() or self.default_output_dir)
        if folder:
            self.output_edit.setText(os.path.abspath(folder))

    def _reset_form(self):
        self.pdf_file = None
        self.file_label.setText("Archivo: (sin seleccionar)")
        self._set_load_status(False)
        self.preview_thumb.setPixmap(QPixmap())
        self.preview_thumb.setText("Sin\nvista previa")
        self.preview_thumb.setStyleSheet(
            "border: 1px solid #CBD5E1; border-radius: 8px; background-color: #F8FAFC; color: #64748B;"
        )
        self.preview_title.setText("(sin seleccionar)")
        self.pages_edit.clear()
        self.output_edit.setText(self.default_output_dir)
        self.progress.setValue(0)

    def _set_load_status(self, loaded, detail=""):
        if loaded:
            self.load_status.setText(f"✅ Archivo cargado: {detail}")
            self.load_status.setStyleSheet(
                "background-color: #ECFDF5; color: #065F46; border: 1px solid #A7F3D0; border-radius: 8px; padding: 6px 10px;"
            )
        else:
            self.load_status.setText("⚪ Archivo no cargado")
            self.load_status.setStyleSheet(
                "background-color: #F8FAFC; color: #64748B; border: 1px solid #E2E8F0; border-radius: 8px; padding: 6px 10px;"
            )

    def _select_pdf(self):
        file, _ = QFileDialog.getOpenFileName(self, "Seleccionar PDF", "", "Archivos PDF (*.pdf)")
        if file:
            self._set_pdf_file(file)

    def _split_pdf(self):
        if not self.pdf_file:
            QMessageBox.warning(self, "Error", "Selecciona un PDF primero.")
            return

        base_output = self.output_edit.text().strip() or self.default_output_dir
        base_output = os.path.abspath(base_output)
        os.makedirs(base_output, exist_ok=True)

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_name = os.path.splitext(os.path.basename(self.pdf_file))[0]
        output_dir = os.path.join(base_output, f"split_{pdf_name}_{stamp}")
        os.makedirs(output_dir, exist_ok=True)

        pages_text = self.pages_edit.text().replace(' ', '')
        if not pages_text:
            QMessageBox.warning(self, "Error", "Indica las páginas a extraer.")
            return
        # Parse pages: 1,3,5-7 -> [0,2,4,5,6]
        page_indexes = []
        for part in pages_text.split(','):
            if '-' in part:
                start, end = part.split('-', 1)
                page_indexes.extend(list(range(int(start)-1, int(end))))
            else:
                page_indexes.append(int(part)-1)
        self.progress.setValue(10)
        try:
            self.controller.split_selected_pages(self.pdf_file, output_dir, page_indexes)
            self.progress.setValue(100)
            QMessageBox.information(self, "Éxito", f"PDF dividido correctamente en:\n{output_dir}")
            self._reset_form()
        except Exception as e:
            self.progress.setValue(0)
            QMessageBox.critical(self, "Error", f"No se pudo dividir el PDF: {e}")
