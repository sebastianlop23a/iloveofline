"""
pdf_compress_view.py - Vista para comprimir PDF e imágenes por límite de tamaño
"""

import os

from PySide6.QtCore import QObject, Signal, QThread

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
    QComboBox,
)

from controllers.pdf_controller import PDFController
from controllers.image_controller import ImageController
from utils.app_paths import get_output_dir
from utils.drag_drop import extract_dropped_paths, filter_existing_files


IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".webp")


class PDFCompressWorker(QObject):
    progress = Signal(int, str)
    finished = Signal(str, float, int)
    failed = Signal(str)

    def __init__(self, controller, source_file, output_path, max_kb):
        super().__init__()
        self.controller = controller
        self.source_file = source_file
        self.output_path = output_path
        self.max_kb = max_kb

    def run(self):
        try:
            result_path, final_kb = self.controller.compress_to_max_kb(
                self.source_file,
                self.output_path,
                max_kb=self.max_kb,
                progress_callback=lambda value, _msg: self.progress.emit(value, _msg),
            )
            self.finished.emit(result_path, final_kb, self.max_kb)
        except Exception as e:
            self.failed.emit(str(e))


class PDFCompressView(QWidget):
    def __init__(self):
        super().__init__()
        self.pdf_controller = PDFController()
        self.image_controller = ImageController()
        self.current_file = None
        self.worker_thread = None
        self.worker = None
        self.active_unit = "KB"
        self.active_target_kb = 100
        self.active_target_display = "100 KB"
        self._init_ui()
        self._on_mode_changed()

    def _init_ui(self):
        self.setAcceptDrops(True)
        layout = QVBoxLayout()

        self.title = QLabel("Comprimir archivos por límite de tamaño")
        self.subtitle = QLabel("Selecciona PDF o imagen y define límite en KB o MB.")

        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(8)
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("PDF", "pdf")
        self.mode_combo.addItem("Imagen", "image")
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_layout.addWidget(QLabel("Tipo:"))
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addStretch()

        self.btn_select = QPushButton("Seleccionar archivo")
        self.btn_select.clicked.connect(self._select_source_file)

        self.file_label = QLabel("Sin archivo seleccionado")
        self.load_status = QLabel()
        self.load_status.setWordWrap(True)
        self._set_load_status(False)

        max_layout = QHBoxLayout()
        max_layout.setSpacing(8)
        self.max_size_input = QLineEdit("100")
        self.max_size_input.setPlaceholderText("Tamaño máximo")
        self.max_size_input.setFixedWidth(120)

        self.unit_combo = QComboBox()
        self.unit_combo.addItem("KB")
        self.unit_combo.addItem("MB")
        self.unit_combo.setFixedWidth(80)

        self.btn_compress = QPushButton("Comprimir")
        self.btn_compress.clicked.connect(self._compress)

        max_layout.addWidget(QLabel("Máximo:"))
        max_layout.addWidget(self.max_size_input)
        max_layout.addWidget(self.unit_combo)
        max_layout.addWidget(self.btn_compress)
        max_layout.addStretch()

        self.progress = QProgressBar()
        self.progress.setValue(0)

        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        layout.addLayout(mode_layout)
        layout.addWidget(self.btn_select)
        layout.addWidget(self.file_label)
        layout.addWidget(self.load_status)
        layout.addLayout(max_layout)
        layout.addWidget(self.progress)
        layout.addStretch()
        self.setLayout(layout)

    def _is_pdf_mode(self):
        return self.mode_combo.currentData() == "pdf"

    def _mode_label(self):
        return "PDF" if self._is_pdf_mode() else "Imagen"

    def _allowed_extensions(self):
        return (".pdf",) if self._is_pdf_mode() else IMAGE_EXTENSIONS

    def _source_file_filter(self):
        if self._is_pdf_mode():
            return "Archivos PDF (*.pdf)"
        return "Imágenes (*.png *.jpg *.jpeg *.bmp *.webp)"

    def _format_size(self, size_kb, unit):
        if unit == "MB":
            return f"{(float(size_kb) / 1024):.2f} MB"
        return f"{float(size_kb):.2f} KB"

    def _on_mode_changed(self):
        if self._is_pdf_mode():
            self.btn_select.setText("Seleccionar PDF")
            self.btn_compress.setText("Comprimir PDF")
            self.subtitle.setText("Ideal para plataformas que exigen tamaño máximo.")
        else:
            self.btn_select.setText("Seleccionar imagen")
            self.btn_compress.setText("Comprimir imagen")
            self.subtitle.setText("Compresión de imágenes integrada en la sección PDF.")

        self.current_file = None
        self.file_label.setText("Sin archivo seleccionado")
        self._set_load_status(False)
        self.progress.setValue(0)

    def dragEnterEvent(self, event):
        dropped_files = filter_existing_files(
            extract_dropped_paths(event.mimeData()),
            allowed_extensions=self._allowed_extensions(),
        )
        if dropped_files:
            event.acceptProposedAction()
            return
        event.ignore()

    def dropEvent(self, event):
        dropped_files = filter_existing_files(
            extract_dropped_paths(event.mimeData()),
            allowed_extensions=self._allowed_extensions(),
        )
        if dropped_files:
            self._set_source_file(dropped_files[0])
            event.acceptProposedAction()
            return
        event.ignore()

    def _set_source_file(self, file_path):
        self.current_file = file_path
        file_name = os.path.basename(file_path)
        self.file_label.setText(f"Archivo: {file_name}")
        self._set_load_status(True, file_name)

    def _set_load_status(self, loaded, detail=""):
        if loaded:
            self.load_status.setText(f"✅ {self._mode_label()} cargado: {detail}")
            self.load_status.setStyleSheet(
                "background-color: #ECFDF5; color: #065F46; border: 1px solid #A7F3D0; border-radius: 8px; padding: 6px 10px;"
            )
        else:
            self.load_status.setText("⚪ Archivo no cargado")
            self.load_status.setStyleSheet(
                "background-color: #F8FAFC; color: #64748B; border: 1px solid #E2E8F0; border-radius: 8px; padding: 6px 10px;"
            )

    def _select_source_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo", "", self._source_file_filter())
        if file_path:
            self._set_source_file(file_path)

    def _read_max_kb(self):
        try:
            raw_text = self.max_size_input.text().strip().replace(",", ".")
            raw_value = float(raw_text)
            if raw_value <= 0:
                raise ValueError()
        except Exception:
            QMessageBox.warning(self, "Error", "Ingresa un valor de tamaño válido.")
            return None, None, None

        unit = self.unit_combo.currentText()
        max_kb = int(round(raw_value * 1024)) if unit == "MB" else int(round(raw_value))
        max_kb = max(1, max_kb)
        return max_kb, f"{raw_value:g} {unit}", unit

    def _compress(self):
        if not self.current_file:
            QMessageBox.warning(self, "Error", f"Selecciona un {self._mode_label().lower()} primero.")
            return

        max_kb, target_display, unit = self._read_max_kb()
        if max_kb is None:
            return

        self.active_unit = unit
        self.active_target_kb = max_kb
        self.active_target_display = target_display

        base_name = os.path.splitext(os.path.basename(self.current_file))[0]
        target_tag = target_display.replace(" ", "").lower().replace(".", "_")

        if self._is_pdf_mode():
            output_dir = get_output_dir("pdf")
            output_path = os.path.join(output_dir, f"{base_name}_{target_tag}.pdf")

            self._set_busy(True)
            self.progress.setValue(5)

            self.worker_thread = QThread(self)
            self.worker = PDFCompressWorker(self.pdf_controller, self.current_file, output_path, max_kb)
            self.worker.moveToThread(self.worker_thread)

            self.worker_thread.started.connect(self.worker.run)
            self.worker.progress.connect(self._on_progress)
            self.worker.finished.connect(self._on_finished)
            self.worker.failed.connect(self._on_failed)

            self.worker.finished.connect(self.worker_thread.quit)
            self.worker.failed.connect(self.worker_thread.quit)
            self.worker_thread.finished.connect(self._cleanup_worker)

            self.worker_thread.start()
            return

        output_dir = get_output_dir("imagenes")
        output_path = os.path.join(output_dir, f"{base_name}_{target_tag}.jpg")

        self._set_busy(True)
        self.progress.setValue(15)
        try:
            _, final_kb = self.image_controller.compress_to_max_kb(self.current_file, output_path, max_kb=max_kb)
            self.progress.setValue(100)
            self._set_busy(False)
            self.subtitle.setText("Compresión finalizada")

            final_text = self._format_size(final_kb, unit)
            if final_kb <= max_kb:
                QMessageBox.information(
                    self,
                    "Éxito",
                    f"Imagen comprimida correctamente.\nTamaño final: {final_text}\nGuardada en:\n{output_path}",
                )
            else:
                QMessageBox.information(
                    self,
                    "Resultado parcial",
                    f"No fue posible llegar a {target_display} exactos.\nMejor resultado: {final_text}\nGuardada en:\n{output_path}",
                )
        except Exception as e:
            self.progress.setValue(0)
            self._set_busy(False)
            self.subtitle.setText("Error en la compresión")
            QMessageBox.critical(self, "Error", f"No se pudo comprimir la imagen: {e}")

    def _set_busy(self, is_busy):
        self.mode_combo.setEnabled(not is_busy)
        self.btn_select.setEnabled(not is_busy)
        self.btn_compress.setEnabled(not is_busy)
        self.max_size_input.setEnabled(not is_busy)
        self.unit_combo.setEnabled(not is_busy)

    def _on_progress(self, value, message):
        self.progress.setValue(max(0, min(100, int(value))))
        if message:
            self.subtitle.setText(message)

    def _on_finished(self, result_path, final_kb, max_kb):
        self.progress.setValue(100)
        self._set_busy(False)
        self.subtitle.setText("Compresión finalizada")

        final_text = self._format_size(final_kb, self.active_unit)
        if final_kb <= max_kb:
            QMessageBox.information(
                self,
                "Éxito",
                f"PDF comprimido correctamente.\nTamaño final: {final_text}\nGuardado en:\n{result_path}",
            )
        else:
            QMessageBox.information(
                self,
                "Resultado parcial",
                f"No fue posible llegar a {self.active_target_display} exactos.\nMejor resultado: {final_text}\nGuardado en:\n{result_path}",
            )

    def _on_failed(self, error_message):
        self.progress.setValue(0)
        self._set_busy(False)
        self.subtitle.setText("Error en la compresión")
        QMessageBox.critical(self, "Error", f"No se pudo comprimir el PDF: {error_message}")

    def _cleanup_worker(self):
        if self.worker is not None:
            self.worker.deleteLater()
            self.worker = None
        if self.worker_thread is not None:
            self.worker_thread.deleteLater()
            self.worker_thread = None


