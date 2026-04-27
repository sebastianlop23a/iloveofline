"""
pdf_merge_preview.py - Vista para unir PDFs con miniaturas y orden
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QListWidget, QListWidgetItem, QListView, QHBoxLayout, QLineEdit, QMessageBox, QProgressBar, QAbstractItemView
from PySide6.QtCore import Qt, QSize, Signal, QTimer
from controllers.pdf_controller import PDFController
from utils.app_paths import get_output_dir
from utils.drag_drop import extract_dropped_paths, filter_existing_files
from utils.pdf_preview import get_first_page_pixmap
import os


class PDFMergeListWidget(QListWidget):
    files_dropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)

    def dragEnterEvent(self, event):
        dropped_files = filter_existing_files(
            extract_dropped_paths(event.mimeData()),
            allowed_extensions=(".pdf",),
        )
        if dropped_files:
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        dropped_files = filter_existing_files(
            extract_dropped_paths(event.mimeData()),
            allowed_extensions=(".pdf",),
        )
        if dropped_files:
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event):
        dropped_files = filter_existing_files(
            extract_dropped_paths(event.mimeData()),
            allowed_extensions=(".pdf",),
        )
        if dropped_files:
            self.files_dropped.emit(dropped_files)
            event.acceptProposedAction()
            return
        super().dropEvent(event)


class PDFMergePreview(QWidget):
    def __init__(self):
        super().__init__()
        self.controller = PDFController()
        self.pdf_files = []
        self._init_ui()

    def _init_ui(self):
        self.setAcceptDrops(True)
        layout = QVBoxLayout()
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)
        self.btn_add = QPushButton("Agregar PDFs")
        self.btn_add.clicked.connect(self._add_pdfs)
        self.list_widget = PDFMergeListWidget()
        self.list_widget.files_dropped.connect(self._add_pdf_files)
        self.list_widget.setSelectionMode(QListWidget.SingleSelection)
        self.list_widget.setViewMode(QListView.IconMode)
        self.list_widget.setFlow(QListView.LeftToRight)
        self.list_widget.setWrapping(True)
        self.list_widget.setResizeMode(QListView.Adjust)
        self.list_widget.setMovement(QListView.Snap)
        self.list_widget.setGridSize(QSize(176, 236))
        self.list_widget.setSpacing(6)
        self.list_widget.setToolTip("Arrastra para cambiar el orden")
        self.list_widget.model().rowsMoved.connect(self._on_rows_moved)

        move_layout = QHBoxLayout()
        self.btn_move_first = QPushButton("⏮ Inicio")
        self.btn_move_first.clicked.connect(self._move_selected_to_start)
        self.btn_move_left = QPushButton("◀ Mover")
        self.btn_move_left.clicked.connect(self._move_selected_left)
        self.btn_move_right = QPushButton("Mover ▶")
        self.btn_move_right.clicked.connect(self._move_selected_right)
        self.btn_move_last = QPushButton("Final ⏭")
        self.btn_move_last.clicked.connect(self._move_selected_to_end)
        move_layout.addWidget(self.btn_move_first)
        move_layout.addWidget(self.btn_move_left)
        move_layout.addWidget(self.btn_move_right)
        move_layout.addWidget(self.btn_move_last)
        move_layout.addStretch()

        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Archivo de salida.pdf")
        self.btn_output = QPushButton("Seleccionar destino")
        self.btn_output.clicked.connect(self._select_output)
        self.btn_merge = QPushButton("Unir PDFs")
        self.btn_merge.clicked.connect(self._merge_pdfs)
        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.btn_add)
        layout.addWidget(self.list_widget)
        layout.addLayout(move_layout)
        out_layout = QHBoxLayout()
        out_layout.addWidget(self.output_edit)
        out_layout.addWidget(self.btn_output)
        layout.addLayout(out_layout)
        layout.addWidget(self.btn_merge)
        layout.addWidget(self.progress)
        self.setLayout(layout)

    def _create_thumbnail_pixmap(self, file_path, size=(120, 160)):
        return get_first_page_pixmap(file_path, max_width=size[0], max_height=size[1])

    def _create_pdf_card_widget(self, file_path):
        container = QWidget()
        container.setFixedSize(170, 230)
        card_layout = QVBoxLayout(container)
        card_layout.setContentsMargins(8, 8, 8, 8)
        card_layout.setSpacing(4)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)

        btn_remove = QPushButton("✕")
        btn_remove.setToolTip("Quitar este PDF")
        btn_remove.setFixedSize(22, 22)
        btn_remove.setCursor(Qt.PointingHandCursor)
        btn_remove.setStyleSheet(
            "QPushButton {"
            "background-color: #FEE2E2;"
            "color: #991B1B;"
            "border: 1px solid #FCA5A5;"
            "border-radius: 11px;"
            "font-weight: 700;"
            "}"
            "QPushButton:hover {"
            "background-color: #FECACA;"
            "}"
        )
        btn_remove.clicked.connect(lambda _=False, target=file_path: self._remove_file(target))

        header_layout.addStretch()
        header_layout.addWidget(btn_remove)

        thumb_label = QLabel()
        thumb_label.setAlignment(Qt.AlignCenter)
        thumb_label.setFixedSize(120, 160)
        thumb_label.setStyleSheet(
            "border: 1px solid #CBD5E1; border-radius: 8px; background-color: #FFFFFF;"
        )

        pixmap = self._create_thumbnail_pixmap(file_path)
        if pixmap and not pixmap.isNull():
            thumb_label.setPixmap(
                pixmap.scaled(112, 152, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        else:
            thumb_label.setText("Sin\nvista previa")
            thumb_label.setStyleSheet(
                "border: 1px solid #CBD5E1; border-radius: 8px; background-color: #F8FAFC; color: #64748B;"
            )

        title_label = QLabel(os.path.basename(file_path))
        title_label.setObjectName("MergeCardTitle")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setWordWrap(True)
        title_label.setFixedWidth(154)

        card_layout.addLayout(header_layout)
        card_layout.addWidget(thumb_label)
        card_layout.addWidget(title_label)
        return container

    def _remove_file(self, file_path):
        ordered_files = [path for path in self._get_ordered_files() if path != file_path]
        self._rebuild_list_from_paths(ordered_files)

    def _refresh_card_titles(self):
        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            file_path = item.data(Qt.UserRole)
            widget = self.list_widget.itemWidget(item)
            if not file_path or widget is None:
                continue
            title_label = widget.findChild(QLabel, "MergeCardTitle")
            if title_label is not None:
                title_label.setText(f"{index + 1}. {os.path.basename(file_path)}")

    def _on_rows_moved(self, *_):
        QTimer.singleShot(0, self._normalize_list_after_reorder)

    def _get_ordered_files(self):
        ordered_files = []
        for index in range(self.list_widget.count()):
            file_path = self.list_widget.item(index).data(Qt.UserRole)
            if file_path:
                ordered_files.append(file_path)
        return ordered_files

    def _rebuild_list_from_paths(self, ordered_files, selected_file=None):
        self.list_widget.clear()
        self.pdf_files = list(ordered_files)

        selected_item = None
        for file_path in ordered_files:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, file_path)
            item.setSizeHint(QSize(170, 230))
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, self._create_pdf_card_widget(file_path))

            if selected_file and file_path == selected_file and selected_item is None:
                selected_item = item

        if selected_item is not None:
            self.list_widget.setCurrentItem(selected_item)

        self._refresh_card_titles()

    def _normalize_list_after_reorder(self):
        selected_item = self.list_widget.currentItem()
        selected_file = selected_item.data(Qt.UserRole) if selected_item else None
        ordered_files = self._get_ordered_files()
        self._rebuild_list_from_paths(ordered_files, selected_file=selected_file)

    def _move_selected_to_index(self, new_index):
        current_index = self.list_widget.currentRow()
        ordered_files = self._get_ordered_files()
        total = len(ordered_files)
        if current_index < 0 or total <= 1:
            return

        new_index = max(0, min(new_index, total - 1))
        if new_index == current_index:
            return

        selected_file = ordered_files.pop(current_index)
        ordered_files.insert(new_index, selected_file)
        self._rebuild_list_from_paths(ordered_files, selected_file=selected_file)

    def _move_selected_left(self):
        self._move_selected_to_index(self.list_widget.currentRow() - 1)

    def _move_selected_right(self):
        self._move_selected_to_index(self.list_widget.currentRow() + 1)

    def _move_selected_to_start(self):
        self._move_selected_to_index(0)

    def _move_selected_to_end(self):
        self._move_selected_to_index(self.list_widget.count() - 1)

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
            self._add_pdf_files(dropped_files)
            event.acceptProposedAction()
            return
        event.ignore()

    def _add_pdf_files(self, files):
        ordered_files = self._get_ordered_files()

        for file in files:
            normalized = os.path.abspath(file)
            if normalized in ordered_files:
                continue

            ordered_files.append(normalized)

        self._rebuild_list_from_paths(ordered_files)

    def _add_pdfs(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Seleccionar PDFs", "", "Archivos PDF (*.pdf)")
        if files:
            self._add_pdf_files(files)

    def _select_output(self):
        default_dir = get_output_dir("pdf")
        default_name = os.path.join(default_dir, "pdf_unido.pdf")
        file, _ = QFileDialog.getSaveFileName(self, "Guardar PDF unido como", default_name, "Archivos PDF (*.pdf)")
        if file:
            if not file.lower().endswith('.pdf'):
                file += '.pdf'
            self.output_edit.setText(os.path.abspath(file))

    def _reset_form(self):
        self.pdf_files = []
        self.list_widget.clear()
        self.output_edit.clear()
        self.progress.setValue(0)

    def _merge_pdfs(self):
        output = self.output_edit.text().strip()
        if self.list_widget.count() == 0 or not output:
            QMessageBox.warning(self, "Error", "Agrega PDFs y define archivo de salida.")
            return

        if not output.lower().endswith('.pdf'):
            output += '.pdf'
            self.output_edit.setText(output)

        output = os.path.abspath(output)
        output_dir = os.path.dirname(output)
        if not output_dir:
            QMessageBox.warning(self, "Error", "Define una ubicación de salida válida.")
            return

        os.makedirs(output_dir, exist_ok=True)

        ordered_files = []
        for i in range(self.list_widget.count()):
            file_path = self.list_widget.item(i).data(Qt.UserRole)
            if file_path:
                ordered_files.append(file_path)

        if not ordered_files:
            QMessageBox.warning(self, "Error", "No hay PDFs válidos para unir.")
            return

        self.progress.setValue(10)
        try:
            self.controller.merge(ordered_files, output)
            self.progress.setValue(100)
            QMessageBox.information(self, "Éxito", f"PDFs unidos correctamente en:\n{output}")
            self._reset_form()
        except Exception as e:
            self.progress.setValue(0)
            QMessageBox.critical(self, "Error", f"No se pudo unir los PDFs: {e}")
