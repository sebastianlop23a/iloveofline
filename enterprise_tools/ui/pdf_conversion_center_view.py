"""
pdf_conversion_center_view.py - Centro de conversiones avanzadas
"""

import os
from datetime import datetime

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QProgressBar,
    QComboBox,
    QHBoxLayout,
    QFrame,
)

from controllers.pdf_controller import PDFController
from utils.app_paths import get_output_dir
from utils.drag_drop import extract_dropped_paths, filter_existing_files


class PDFConversionCenterView(QWidget):
    def __init__(self):
        super().__init__()
        self.controller = PDFController()
        self.operations = self.controller.get_conversion_operations()
        self.operations_by_key = {item["key"]: item for item in self.operations}
        self.source_files = []
        self.last_result_path = ""
        self._init_ui()

    def _init_ui(self):
        self.setAcceptDrops(True)
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        title = QLabel("Centro de conversiones")
        title.setObjectName("Title")

        subtitle = QLabel(
            "Convierte entre PDF, Office, imágenes, TXT y HTML desde un único flujo."
        )
        subtitle.setObjectName("Subtitle")
        subtitle.setWordWrap(True)

        card = QFrame()
        card.setObjectName("MainCard")

        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(10)

        self.operation_combo = QComboBox()
        for item in self.operations:
            self.operation_combo.addItem(item["label"], item["key"])
        self.operation_combo.currentIndexChanged.connect(self._on_operation_changed)

        self.filter_label = QLabel("")
        self.filter_label.setObjectName("Subtitle")
        self.filter_label.setWordWrap(True)

        file_row = QHBoxLayout()
        file_row.setSpacing(8)

        self.select_button = QPushButton("Seleccionar archivo origen")
        self.select_button.clicked.connect(self._select_source_file)

        self.convert_button = QPushButton("Convertir")
        self.convert_button.setObjectName("PrimaryButton")
        self.convert_button.clicked.connect(self._convert)

        self.open_result_button = QPushButton("Abrir resultado")
        self.open_result_button.clicked.connect(self._open_result)
        self.open_result_button.setEnabled(False)

        file_row.addWidget(self.select_button)
        file_row.addWidget(self.convert_button)
        file_row.addWidget(self.open_result_button)
        file_row.addStretch()

        self.source_label = QLabel("Archivo(s) origen: (sin seleccionar)")
        self.source_label.setWordWrap(True)

        self.load_status = QLabel()
        self.load_status.setWordWrap(True)
        self._set_load_status(False)

        self.output_preview = QLabel("Salida automática: se guardará en la carpeta de conversiones")
        self.output_preview.setObjectName("Subtitle")
        self.output_preview.setWordWrap(True)

        self.notice_label = QLabel(
            "Nota: PDF→DOCX requiere 'pdf2docx'."
        )
        self.notice_label.setObjectName("Subtitle")
        self.notice_label.setWordWrap(True)

        self.progress = QProgressBar()
        self.progress.setValue(0)

        card_layout.addWidget(QLabel("Tipo de conversión"))
        card_layout.addWidget(self.operation_combo)
        card_layout.addWidget(self.filter_label)
        card_layout.addLayout(file_row)
        card_layout.addWidget(self.source_label)
        card_layout.addWidget(self.load_status)
        card_layout.addWidget(self.output_preview)
        card_layout.addWidget(self.notice_label)
        card_layout.addWidget(self.progress)
        card.setLayout(card_layout)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(card)
        layout.addStretch()

        self.setLayout(layout)
        self._on_operation_changed()

    def dragEnterEvent(self, event):
        operation = self._get_current_operation()
        if not operation:
            event.ignore()
            return

        dropped_files = filter_existing_files(
            extract_dropped_paths(event.mimeData()),
            allowed_extensions=tuple(operation["source_extensions"]),
        )
        if dropped_files:
            event.acceptProposedAction()
            return

        event.ignore()

    def dropEvent(self, event):
        operation = self._get_current_operation()
        if not operation:
            event.ignore()
            return

        dropped_files = filter_existing_files(
            extract_dropped_paths(event.mimeData()),
            allowed_extensions=tuple(operation["source_extensions"]),
        )
        if not dropped_files:
            event.ignore()
            return

        if operation["key"] != "image_to_pdf":
            dropped_files = [dropped_files[0]]

        self._apply_source_files(dropped_files, operation)
        event.acceptProposedAction()

    def _apply_source_files(self, files, operation):
        self.source_files = [os.path.abspath(path) for path in files]

        if operation["key"] == "image_to_pdf":
            display = ", ".join(os.path.basename(path) for path in self.source_files[:3])
            if len(self.source_files) > 3:
                display += f" (+{len(self.source_files) - 3} más)"
            self.source_label.setText(f"Archivo(s) origen: {display}")
            self._set_load_status(True, f"{len(self.source_files)} archivo(s)")
            preview_target = self._build_output_target(self.source_files[0], operation)
        else:
            file_name = os.path.basename(self.source_files[0])
            self.source_label.setText(f"Archivo(s) origen: {file_name}")
            self._set_load_status(True, file_name)
            preview_target = self._build_output_target(self.source_files[0], operation)

        self.last_result_path = ""
        self.open_result_button.setEnabled(False)
        self.output_preview.setText(f"Salida automática: {preview_target}")

    def _get_current_operation(self):
        operation_key = self.operation_combo.currentData()
        return self.operations_by_key.get(operation_key)

    def _on_operation_changed(self):
        operation = self._get_current_operation()
        if not operation:
            self.filter_label.setText("Formato origen: no disponible")
            return

        extensions = ", ".join(operation["source_extensions"])
        output_kind_text = "carpeta" if operation["output_kind"] == "folder" else operation["output_extension"]
        self.filter_label.setText(
            f"Formato origen permitido: {extensions} | Salida: {output_kind_text}"
        )
        self.source_files = []
        self.source_label.setText("Archivo(s) origen: (sin seleccionar)")
        self._set_load_status(False)
        self.progress.setValue(0)

    def _set_load_status(self, loaded, detail=""):
        if loaded:
            self.load_status.setText(f"✅ Origen cargado: {detail}")
            self.load_status.setStyleSheet(
                "background-color: #ECFDF5; color: #065F46; border: 1px solid #A7F3D0; border-radius: 8px; padding: 6px 10px;"
            )
        else:
            self.load_status.setText("⚪ Origen no cargado")
            self.load_status.setStyleSheet(
                "background-color: #F8FAFC; color: #64748B; border: 1px solid #E2E8F0; border-radius: 8px; padding: 6px 10px;"
            )

    def _select_source_file(self):
        operation = self._get_current_operation()
        if not operation:
            return

        is_multi_image = operation["key"] == "image_to_pdf"

        if is_multi_image:
            files, _ = QFileDialog.getOpenFileNames(
                self,
                "Seleccionar imágenes origen",
                "",
                operation["source_filter"],
            )
            if not files:
                return
            self._apply_source_files(files, operation)
        else:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Seleccionar archivo origen",
                "",
                operation["source_filter"],
            )
            if not file_path:
                return
            self._apply_source_files([file_path], operation)

    def _build_output_target(self, source_file: str, operation: dict) -> str:
        output_root = get_output_dir("conversiones")
        base_name = os.path.splitext(os.path.basename(source_file))[0]
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if operation["output_kind"] == "folder":
            return os.path.join(output_root, f"{base_name}_{operation['key']}_{stamp}")

        output_extension = operation["output_extension"] or ".out"
        return os.path.join(output_root, f"{base_name}_{operation['key']}{output_extension}")

    def _convert(self):
        operation = self._get_current_operation()
        if not operation:
            QMessageBox.warning(self, "Error", "No hay operación seleccionada.")
            return

        if not self.source_files:
            QMessageBox.warning(self, "Error", "Selecciona un archivo origen válido.")
            return

        for source_file in self.source_files:
            if not os.path.isfile(source_file):
                QMessageBox.warning(self, "Error", f"Archivo no encontrado:\n{source_file}")
                return

        for source_file in self.source_files:
            source_ext = os.path.splitext(source_file)[1].lower()
            if source_ext not in operation["source_extensions"]:
                QMessageBox.warning(
                    self,
                    "Formato no permitido",
                    f"Esta operación admite: {', '.join(operation['source_extensions'])}",
                )
                return

        output_target = self._build_output_target(self.source_files[0], operation)

        self.progress.setValue(12)
        try:
            conversion_input = self.source_files
            if operation["key"] != "image_to_pdf":
                conversion_input = self.source_files[0]

            result_path = self.controller.execute_conversion(
                operation["key"],
                conversion_input,
                output_target,
            )
            self.progress.setValue(100)
            self.last_result_path = result_path
            self.open_result_button.setEnabled(True)
            self.output_preview.setText(f"Resultado: {result_path}")
            QMessageBox.information(self, "Conversión completada", f"Resultado generado en:\n{result_path}")
        except Exception as exc:
            self.progress.setValue(0)
            QMessageBox.critical(self, "Error", f"No se pudo convertir el archivo:\n{exc}")

    def _open_result(self):
        if not self.last_result_path:
            return

        open_path = self.last_result_path
        if os.path.isfile(open_path):
            open_path = os.path.dirname(open_path)

        os.makedirs(open_path, exist_ok=True)
        if hasattr(os, "startfile"):
            os.startfile(open_path)
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(open_path))
