"""
pdf_decrypt_view.py - Vista para quitar contraseña a PDFs
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QLineEdit, QMessageBox, QProgressBar, QInputDialog
from controllers.pdf_controller import PDFController
from utils.app_paths import get_output_dir
from utils.drag_drop import extract_dropped_paths, filter_existing_directories, filter_existing_files
import os
import tempfile
import shutil
from utils.pdf_bulk_decrypt import remove_weak_pdf_protection_in_folder


class PDFDecryptView(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        self.setAcceptDrops(True)
        layout = QVBoxLayout()
        self.label = QLabel("Desencriptar PDFs (carpeta o archivo individual)")
        self.btn_select = QPushButton("Seleccionar carpeta o PDF protegido")
        self.btn_select.clicked.connect(self._select_path)
        self.selection_label = QLabel("Origen: (sin seleccionar)")
        self.load_status = QLabel()
        self.load_status.setWordWrap(True)
        self._set_load_status(False)
        self.btn_decrypt = QPushButton("Procesar y quitar protecciones")
        self.btn_decrypt.clicked.connect(self._decrypt)
        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.label)
        layout.addWidget(self.btn_select)
        layout.addWidget(self.selection_label)
        layout.addWidget(self.load_status)
        layout.addWidget(self.btn_decrypt)
        layout.addWidget(self.progress)
        self.setLayout(layout)
        self.selected_path = None

    def dragEnterEvent(self, event):
        dropped_paths = extract_dropped_paths(event.mimeData())
        dropped_dirs = filter_existing_directories(dropped_paths)
        dropped_pdfs = filter_existing_files(dropped_paths, allowed_extensions=(".pdf",))
        if dropped_dirs or dropped_pdfs:
            event.acceptProposedAction()
            return
        event.ignore()

    def dropEvent(self, event):
        dropped_paths = extract_dropped_paths(event.mimeData())
        dropped_dirs = filter_existing_directories(dropped_paths)
        dropped_pdfs = filter_existing_files(dropped_paths, allowed_extensions=(".pdf",))

        selected = None
        if dropped_dirs:
            selected = dropped_dirs[0]
            detail = os.path.basename(selected)
            self.selection_label.setText(f"Carpeta seleccionada: {detail}")
            self._set_load_status(True, detail)
        elif dropped_pdfs:
            selected = dropped_pdfs[0]
            detail = os.path.basename(selected)
            self.selection_label.setText(f"PDF seleccionado: {detail}")
            self._set_load_status(True, detail)

        if selected:
            self.selected_path = selected
            event.acceptProposedAction()
            return

        event.ignore()

    def _set_load_status(self, loaded, detail=""):
        if loaded:
            self.load_status.setText(f"✅ Archivo/carpeta cargado: {detail}")
            self.load_status.setStyleSheet(
                "background-color: #ECFDF5; color: #065F46; border: 1px solid #A7F3D0; border-radius: 8px; padding: 6px 10px;"
            )
        else:
            self.load_status.setText("⚪ Origen no cargado")
            self.load_status.setStyleSheet(
                "background-color: #F8FAFC; color: #64748B; border: 1px solid #E2E8F0; border-radius: 8px; padding: 6px 10px;"
            )

    def _select_path(self):
        # Primero preguntar si quiere carpeta o archivo
        from PySide6.QtWidgets import QMessageBox
        choice = QMessageBox.question(self, "Tipo de selección", "¿Quieres seleccionar una carpeta (Sí) o un PDF individual (No)?", QMessageBox.Yes | QMessageBox.No)
        if choice == QMessageBox.Yes:
            folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta de PDFs protegidos", "")
            if folder:
                self.selected_path = folder
                folder_name = os.path.basename(folder)
                self.selection_label.setText(f"Carpeta seleccionada: {folder_name}")
                self._set_load_status(True, folder_name)
                return
        file, _ = QFileDialog.getOpenFileName(self, "Seleccionar PDF protegido", "", "Archivos PDF (*.pdf)")
        if file:
            self.selected_path = file
            file_name = os.path.basename(file)
            self.selection_label.setText(f"PDF seleccionado: {file_name}")
            self._set_load_status(True, file_name)

    def _decrypt(self):
        if not self.selected_path:
            QMessageBox.warning(self, "Error", "Selecciona una carpeta o PDF primero.")
            return
        self.progress.setValue(10)
        try:
            if os.path.isdir(self.selected_path):
                remove_weak_pdf_protection_in_folder(self.selected_path)
            else:
                from utils.pdf_bulk_decrypt import quitar_contraseña_apertura_pdf
                pdf_output_dir = get_output_dir("pdf")
                base_name = os.path.splitext(os.path.basename(self.selected_path))[0]
                output_pdf = os.path.join(pdf_output_dir, f"{base_name}_desencriptado.pdf")
                password = None
                intentos = 0
                while True:
                    ok = quitar_contraseña_apertura_pdf(self.selected_path, output_pdf, password)
                    if ok:
                        break
                    # Si falló, pedir contraseña al usuario con cuadro de diálogo
                    intentos += 1
                    if intentos > 3:
                        raise Exception("Demasiados intentos fallidos de contraseña.")
                    password, ok_dialog = QInputDialog.getText(self, "Contraseña incorrecta", "La contraseña es incorrecta. Intenta de nuevo:", QLineEdit.Password)
                    if not ok_dialog or not password:
                        raise Exception("No se proporcionó contraseña de apertura.")
            self.progress.setValue(100)
            if os.path.isdir(self.selected_path):
                QMessageBox.information(self, "Éxito", "Se procesó correctamente. Revisa la consola para detalles.")
            else:
                QMessageBox.information(self, "Éxito", f"PDF desencriptado guardado en:\n{output_pdf}")
        except Exception as e:
            self.progress.setValue(0)
            QMessageBox.critical(self, "Error", f"No se pudo procesar: {e}")
