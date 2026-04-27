"""
history_view.py - UI para el historial de acciones
"""

import os

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QTreeView,
    QFileSystemModel,
    QPushButton,
    QHBoxLayout,
    QComboBox,
    QMessageBox,
)
from PySide6.QtCore import Qt, QDir, QSortFilterProxyModel, QModelIndex
from services.history_service import HistoryService
from utils.app_paths import get_app_home


class AppCreatedFilesProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.allowed_files = set()
        self.allowed_dirs = set()
        self.allowed_roots = set()

    def set_allowed_paths(self, paths, roots=None):
        self.allowed_files.clear()
        self.allowed_dirs.clear()
        self.allowed_roots.clear()

        for root in roots or []:
            if root:
                normalized_root = os.path.normcase(os.path.abspath(os.path.normpath(root)))
                self.allowed_roots.add(normalized_root)
                self._add_parent_dirs(normalized_root)

        for raw_path in paths:
            if not raw_path:
                continue

            normalized = os.path.normcase(os.path.abspath(os.path.normpath(raw_path)))

            if os.path.isfile(normalized):
                self.allowed_files.add(normalized)
                folder = os.path.dirname(normalized)
                self._add_parent_dirs(folder)
            elif os.path.isdir(normalized):
                self._add_parent_dirs(normalized)

        self.invalidateFilter()

    def _add_parent_dirs(self, start_dir):
        current = os.path.normcase(os.path.abspath(start_dir))
        while current and current not in self.allowed_dirs:
            self.allowed_dirs.add(current)
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent

    def filterAcceptsRow(self, source_row, source_parent):
        source_model = self.sourceModel()
        if source_model is None:
            return False

        source_index = source_model.index(source_row, 0, source_parent)
        if not source_index.isValid():
            return False

        path = source_model.filePath(source_index)
        if not path:
            return False

        normalized = os.path.normcase(os.path.abspath(os.path.normpath(path)))

        for root in self.allowed_roots:
            if normalized == root or normalized.startswith(root + os.sep):
                return True

        if os.path.isdir(normalized):
            return normalized in self.allowed_dirs
        return normalized in self.allowed_files


class HistoryView(QWidget):
    def __init__(self):
        super().__init__()
        self.model = None
        self.proxy_model = None

        layout = QVBoxLayout()

        self.title = QLabel("Historial - Explorador de archivos")
        self.title.setAlignment(Qt.AlignLeft)
        self.subtitle = QLabel("Vista tipo explorador de Windows con los directorios usados por la app")
        self.subtitle.setStyleSheet("color: #6B7280;")

        root_row = QHBoxLayout()
        self.root_label = QLabel("Ubicación:")
        self.root_combo = QComboBox()
        self.root_combo.currentTextChanged.connect(self._on_root_changed)
        root_row.addWidget(self.root_label)
        root_row.addWidget(self.root_combo)

        controls = QHBoxLayout()
        self.btn_refresh = QPushButton("Refrescar")
        self.btn_refresh.clicked.connect(self.load_history)
        self.btn_open = QPushButton("Abrir seleccionado")
        self.btn_open.clicked.connect(self.open_selected)
        self.btn_clear = QPushButton("Limpiar historial")
        self.btn_clear.clicked.connect(self.clear_history)
        controls.addWidget(self.btn_refresh)
        controls.addWidget(self.btn_open)
        controls.addWidget(self.btn_clear)
        controls.addStretch()

        self.history_tree = QTreeView()
        self.history_tree.setAlternatingRowColors(True)
        self.history_tree.setSortingEnabled(True)
        self.history_tree.setAnimated(True)
        self.history_tree.doubleClicked.connect(self.open_item)

        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        layout.addLayout(root_row)
        layout.addLayout(controls)
        layout.addWidget(self.history_tree)

        self.setLayout(layout)
        self._init_model()
        self.load_history()

    def _init_model(self):
        self.model = QFileSystemModel(self)
        self.model.setReadOnly(True)
        self.model.setFilter(QDir.AllDirs | QDir.Files | QDir.NoDotAndDotDot)
        self.proxy_model = AppCreatedFilesProxyModel(self)
        self.proxy_model.setSourceModel(self.model)
        self.history_tree.setModel(self.proxy_model)

    def load_history(self):
        app_home = get_app_home()
        files = HistoryService.get_created_files(limit=1000)
        created_paths = []
        for item in files:
            item_path = item.get("path") or ""
            if item_path and os.path.exists(item_path):
                created_paths.append(item_path)

        roots = [app_home]
        self.proxy_model.set_allowed_paths(created_paths, roots=roots)

        self.root_combo.blockSignals(True)
        self.root_combo.clear()
        self.root_combo.addItems(roots)
        self.root_combo.blockSignals(False)

        self._set_root_path(app_home)

    def _on_root_changed(self, path):
        if path:
            self._set_root_path(path)

    def _set_root_path(self, path):
        source_root = self.model.setRootPath(path)
        proxy_root = self.proxy_model.mapFromSource(source_root)
        self.history_tree.setRootIndex(proxy_root)
        self.history_tree.resizeColumnToContents(0)

    def open_item(self, index):
        source_index = self.proxy_model.mapToSource(index)
        path = self.model.filePath(source_index)
        if not path:
            return
        if not os.path.exists(path):
            QMessageBox.warning(self, "No encontrado", "La ruta ya no existe en el sistema.")
            return
        try:
            if os.path.isfile(path):
                os.startfile(path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir la ruta: {e}")

    def open_selected(self):
        current = self.history_tree.currentIndex()
        if not current.isValid():
            QMessageBox.information(self, "Selecciona un elemento", "Selecciona un archivo o carpeta para abrir.")
            return

        source_index = self.proxy_model.mapToSource(current)
        path = self.model.filePath(source_index)
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "No encontrado", "La ruta ya no existe en el sistema.")
            return

        try:
            os.startfile(path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir la ruta: {e}")

    def clear_history(self):
        confirm = QMessageBox.question(
            self,
            "Confirmar",
            "¿Seguro que deseas limpiar el historial?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        HistoryService.clear_history()
        self.load_history()
