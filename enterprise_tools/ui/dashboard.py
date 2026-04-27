"""
dashboard.py - Main dashboard UI for Enterprise Tools Suite
"""

import os
import sys

if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from PySide6.QtCore import Qt, QSize, QUrl
from PySide6.QtGui import QIcon, QPixmap, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QLabel,
    QHBoxLayout,
    QListWidget,
    QPushButton,
    QStackedWidget,
    QListWidgetItem,
    QLineEdit,
)

try:
    import qtawesome as qta
except Exception:
    qta = None

from ui.home_view import HomeView
from ui.zip_view import ZipView
from ui.pdf_view import PDFView
from ui.history_view import HistoryView
from ui.faq_view import FAQView
from ui.task_manager_view import TaskManagerView
from utils.app_paths import get_app_home
from utils.log_security import request_logs_access


class DashboardWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self._context_expanded_width = 244
        self._workbench_min_ratio = 0.70

        self.setWindowTitle("Herramientas Internas Avista")
        self._apply_window_icon()
        self.setMinimumSize(1100, 700)
        self.resize(1400, 860)

        self.page_definitions = []

        self._init_ui()
        self._apply_styles()

        self.statusBar().showMessage("Sistema listo")

    def _apply_window_icon(self):
        candidate_rel_paths = [
            os.path.join("assets", "iconoavis.ico"),
            os.path.join("assets", "iconoaavis.ico"),
            os.path.join("assets", "app_icon.ico"),
            os.path.join("assets", "app_icon.png"),
            os.path.join("assets", "avista_logo.png"),
        ]

        for relative_path in candidate_rel_paths:
            candidate = self._resource_path(relative_path)
            if not os.path.isfile(candidate):
                continue

            icon = QIcon(candidate)
            if icon.isNull():
                continue

            self.setWindowIcon(icon)
            app = QApplication.instance()
            if app is not None and app.windowIcon().isNull():
                app.setWindowIcon(icon)
            return

    # ================= UI =================

    def _init_ui(self):
        central_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ===== Top bar =====
        top_bar = QWidget()
        top_bar.setObjectName("TopBar")
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(18, 10, 18, 10)
        top_layout.setSpacing(12)

        logo = QLabel("AVISTA")
        logo.setObjectName("LogoLabel")
        self._apply_logo_image(logo)

        title = QLabel("Enterprise Tools Suite")
        title.setObjectName("HeaderTitle")

        subtitle = QLabel("Centro de utilidades internas")
        subtitle.setObjectName("HeaderSubtitle")

        title_container = QVBoxLayout()
        title_container.setContentsMargins(0, 0, 0, 0)
        title_container.setSpacing(2)
        title_container.addWidget(title)
        title_container.addWidget(subtitle)

        brand_container = QWidget()
        brand_layout = QHBoxLayout()
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(10)
        brand_layout.addWidget(logo)
        brand_layout.addLayout(title_container)
        brand_container.setLayout(brand_layout)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("TopSearch")
        self.search_input.setPlaceholderText("Buscar módulo...")
        self.search_input.setFixedWidth(320)
        self.search_input.textChanged.connect(self._filter_navigation)

        home_button = QPushButton("Inicio")
        home_button.setObjectName("TopQuickBtn")
        home_button.clicked.connect(lambda: self._navigate_to(0))

        output_button = QPushButton("Salida")
        output_button.setObjectName("TopQuickBtn")
        output_button.clicked.connect(self._open_app_home)

        logs_button = QPushButton("Logs")
        logs_button.setObjectName("TopQuickBtn")
        logs_button.clicked.connect(self._open_logs)

        self.context_toggle = QPushButton("Contexto")
        self.context_toggle.setObjectName("TopQuickBtn")
        self.context_toggle.setCheckable(True)
        self.context_toggle.setChecked(False)
        self.context_toggle.setToolTip("Mostrar u ocultar panel de contexto")
        self.context_toggle.toggled.connect(self._toggle_context_panel)

        top_layout.addWidget(brand_container)
        top_layout.addStretch()
        top_layout.addWidget(self.search_input)
        top_layout.addWidget(home_button)
        top_layout.addWidget(output_button)
        top_layout.addWidget(logs_button)
        top_layout.addWidget(self.context_toggle)
        top_bar.setLayout(top_layout)

        # ===== Content area =====
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.page_definitions = self._build_page_definitions()

        # Navigation rail
        self.nav_shell = QWidget()
        self.nav_shell.setObjectName("NavShell")
        self.nav_shell.setFixedWidth(238)

        nav_layout = QVBoxLayout()
        nav_layout.setContentsMargins(0, 16, 0, 16)
        nav_layout.setSpacing(8)

        nav_title = QLabel("MÓDULOS")
        nav_title.setObjectName("NavTitle")

        self.menu = QListWidget()
        self.menu.setObjectName("NavMenu")
        self.menu.setIconSize(QSize(18, 18))
        self.menu.setSpacing(2)

        for page in self.page_definitions:
            item = QListWidgetItem(self._get_nav_icon(page["icon"]), page["label"])
            item.setData(Qt.UserRole, page["keywords"])
            self.menu.addItem(item)

        self.menu.currentRowChanged.connect(self._change_tool)

        nav_layout.addWidget(nav_title)
        nav_layout.addWidget(self.menu)
        self.nav_shell.setLayout(nav_layout)

        # Workbench center
        workbench_shell = QWidget()
        workbench_shell.setObjectName("WorkbenchShell")
        workbench_layout = QVBoxLayout()
        workbench_layout.setContentsMargins(16, 14, 16, 14)

        self.stack = QStackedWidget()
        self.stack.setObjectName("WorkbenchStack")

        for page in self.page_definitions:
            self.stack.addWidget(page["widget"])

        workbench_layout.addWidget(self.stack)
        workbench_shell.setLayout(workbench_layout)

        # Context panel (right)
        self.context_panel = QWidget()
        self.context_panel.setObjectName("ContextPanel")
        self.context_panel.setFixedWidth(self._context_expanded_width)
        self.context_panel.setVisible(False)

        context_layout = QVBoxLayout()
        context_layout.setContentsMargins(16, 18, 16, 18)
        context_layout.setSpacing(10)

        context_title = QLabel("Contexto")
        context_title.setObjectName("ContextTitle")

        self.context_module = QLabel("-")
        self.context_module.setObjectName("ContextModule")

        self.context_description = QLabel("-")
        self.context_description.setObjectName("ContextDescription")
        self.context_description.setWordWrap(True)

        context_actions_title = QLabel("Atajos")
        context_actions_title.setObjectName("ContextActionsTitle")

        self.context_actions_container = QWidget()
        self.context_actions_layout = QVBoxLayout()
        self.context_actions_layout.setContentsMargins(0, 0, 0, 0)
        self.context_actions_layout.setSpacing(8)
        self.context_actions_container.setLayout(self.context_actions_layout)

        context_layout.addWidget(context_title)
        context_layout.addWidget(self.context_module)
        context_layout.addWidget(self.context_description)
        context_layout.addSpacing(6)
        context_layout.addWidget(context_actions_title)
        context_layout.addWidget(self.context_actions_container)
        context_layout.addStretch()
        self.context_panel.setLayout(context_layout)

        content_layout.addWidget(self.nav_shell)
        content_layout.addWidget(workbench_shell, 1)
        content_layout.addWidget(self.context_panel)

        main_layout.addWidget(top_bar)
        main_layout.addLayout(content_layout)

        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        self.menu.setCurrentRow(0)
        self._ensure_workbench_ratio()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._ensure_workbench_ratio()

    def _build_page_definitions(self):
        home_view = HomeView()
        home_view.module_requested.connect(self._navigate_to)

        return [
            {
                "label": "Inicio",
                "icon": "home",
                "keywords": "inicio panel centro mando",
                "widget": home_view,
                "description": "Vista general con accesos rápidos para ejecutar tareas frecuentes.",
                "actions": [
                    ("Abrir carpeta de trabajo", self._open_app_home),
                    ("Abrir logs", self._open_logs),
                    ("Ir a PDF", lambda: self._navigate_to(2)),
                ],
            },
            {
                "label": "Descompresión ZIP",
                "icon": "zip",
                "keywords": "zip comprimir descomprimir extraer",
                "widget": ZipView(),
                "description": "Extrae archivos ZIP y controla la carpeta de destino dentro del entorno de la app.",
                "actions": [
                    ("Abrir salida", self._open_app_home),
                    ("Ir a Historial", lambda: self._navigate_to(3)),
                ],
            },
            {
                "label": "PDF",
                "icon": "pdf",
                "keywords": "pdf unir dividir convertir comprimir",
                "widget": PDFView(),
                "description": "Suite PDF con flujo guiado para combinación, división, conversión y compresión.",
                "actions": [
                    ("Ir a Herramientas PDF", lambda: self._navigate_to(2)),
                    ("Abrir salida", self._open_app_home),
                ],
            },
            {
                "label": "Explorador de archivos",
                "icon": "history",
                "keywords": "historial archivos explorador",
                "widget": HistoryView(),
                "description": "Explora y abre los archivos generados por las herramientas en una sola vista.",
                "actions": [
                    ("Refrescar módulo", lambda: self._navigate_to(3)),
                    ("Abrir carpeta de trabajo", self._open_app_home),
                ],
            },
            {
                "label": "Guías y Ayuda",
                "icon": "help",
                "keywords": "faq ayuda guias soporte",
                "widget": FAQView(),
                "description": "Documentación de soporte interno y soluciones rápidas por caso de uso.",
                "actions": [
                    ("Ir a Inicio", lambda: self._navigate_to(0)),
                    ("Abrir logs", self._open_logs),
                ],
            },
            {
                "label": "Administrador de tareas",
                "icon": "tasks",
                "keywords": "tareas procesos cpu ram disco optimizar rendimiento",
                "widget": TaskManagerView(),
                "description": "Monitoreo inteligente del sistema con recomendaciones y optimización segura del equipo.",
                "actions": [
                    ("Ir al módulo", lambda: self._navigate_to(5)),
                    ("Abrir logs", self._open_logs),
                ],
            },
        ]

    # ================= Resources =================

    def _resource_path(self, relative_path: str) -> str:
        if getattr(sys, "frozen", False):
            base_path = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        else:
            base_path = os.path.dirname(os.path.dirname(__file__))
        return os.path.join(base_path, relative_path)

    def _resolve_logo_path(self):
        candidate_rel_paths = [
            os.path.join("assets", "avista_logo.png"),
            os.path.join("assets", "logo.png"),
            os.path.join("assets", "logo.jpg"),
            os.path.join("assets", "logo.jpeg"),
            os.path.join("assets", "logo.webp"),
        ]

        if getattr(sys, "frozen", False):
            base_paths = [
                getattr(sys, "_MEIPASS", ""),
                os.path.dirname(sys.executable),
            ]
        else:
            app_root = os.path.dirname(os.path.dirname(__file__))
            workspace_root = os.path.dirname(app_root)
            base_paths = [app_root, workspace_root]

        for relative_path in candidate_rel_paths:
            for base_path in base_paths:
                if not base_path:
                    continue

                direct_path = os.path.join(base_path, relative_path)
                if os.path.isfile(direct_path):
                    return direct_path

                nested_path = os.path.join(base_path, "enterprise_tools", relative_path)
                if os.path.isfile(nested_path):
                    return nested_path

        return ""

    def _apply_logo_image(self, logo_label: QLabel):
        logo_path = self._resolve_logo_path()
        if not os.path.isfile(logo_path):
            return

        pixmap = QPixmap(logo_path)
        if pixmap.isNull():
            return

        scaled = pixmap.scaledToHeight(44, Qt.SmoothTransformation)
        logo_label.setPixmap(scaled)
        logo_label.setText("")
        logo_label.setMinimumWidth(max(126, scaled.width() + 8))

    def _get_nav_icon(self, icon_name: str) -> QIcon:
        qtawesome_map = {
            "home": "fa5s.th-large",
            "zip": "fa5s.file-archive",
            "pdf": "fa5s.file-pdf",
            "image": "fa5s.image",
            "history": "fa5s.folder-open",
            "help": "fa5s.question-circle",
            "tasks": "fa5s.tasks",
        }

        if qta is not None:
            try:
                return qta.icon(qtawesome_map.get(icon_name, "fa5s.circle"), color="#CBD5E1")
            except Exception:
                return QIcon()
        return QIcon()

    # ================= Navigation =================

    def _change_tool(self, index: int):
        if not (0 <= index < len(self.page_definitions)):
            return

        self.stack.setCurrentIndex(index)
        page = self.page_definitions[index]
        self._update_context_panel(page)
        self.statusBar().showMessage(f"Módulo activo: {page['label']}")
        self._ensure_workbench_ratio()

    def _toggle_context_panel(self, visible: bool):
        self.context_panel.setVisible(bool(visible))
        if visible:
            self.context_panel.setFixedWidth(self._context_expanded_width)
        self._ensure_workbench_ratio()

    def _ensure_workbench_ratio(self):
        if not hasattr(self, "context_panel") or not hasattr(self, "nav_shell"):
            return

        if not self.context_panel.isVisible():
            return

        total_width = max(1, self.width())
        nav_width = self.nav_shell.width() if self.nav_shell.width() > 0 else 238
        max_context_width = int(total_width * (1 - self._workbench_min_ratio)) - nav_width
        max_context_width = max(0, max_context_width)

        if max_context_width < 140:
            self.context_panel.setVisible(False)
            if hasattr(self, "context_toggle"):
                self.context_toggle.blockSignals(True)
                self.context_toggle.setChecked(False)
                self.context_toggle.blockSignals(False)
            return

        self.context_panel.setFixedWidth(min(self._context_expanded_width, max_context_width))

    def _navigate_to(self, index: int):
        if not (0 <= index < len(self.page_definitions)):
            return

        item = self.menu.item(index)
        if item and item.isHidden():
            self.search_input.clear()

        self.menu.setCurrentRow(index)

    def _filter_navigation(self, text: str):
        query = text.strip().lower()
        visible_indices = []

        for row in range(self.menu.count()):
            item = self.menu.item(row)
            item_text = item.text().lower()
            item_keywords = (item.data(Qt.UserRole) or "").lower()
            is_visible = query in item_text or query in item_keywords if query else True
            item.setHidden(not is_visible)
            if is_visible:
                visible_indices.append(row)

        if not visible_indices:
            self.statusBar().showMessage("No hay módulos que coincidan con la búsqueda", 2200)
            return

        current = self.menu.currentRow()
        if current not in visible_indices:
            self.menu.setCurrentRow(visible_indices[0])

    # ================= Context panel =================

    def _update_context_panel(self, page: dict):
        self.context_module.setText(page["label"])
        self.context_description.setText(page["description"])
        self._render_context_actions(page.get("actions", []))

    def _render_context_actions(self, actions):
        while self.context_actions_layout.count():
            child = self.context_actions_layout.takeAt(0)
            widget = child.widget()
            if widget is not None:
                widget.deleteLater()

        for text, callback in actions:
            button = QPushButton(text)
            button.setObjectName("ContextActionButton")
            button.clicked.connect(callback)
            self.context_actions_layout.addWidget(button)

    # ================= Quick actions =================

    def _open_app_home(self):
        self._open_path(get_app_home())

    def _open_logs(self):
        logs_path = request_logs_access(self)
        if not logs_path:
            return
        self._open_path(logs_path)

    def _open_path(self, path: str):
        os.makedirs(path, exist_ok=True)
        if hasattr(os, "startfile"):
            os.startfile(path)
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    # ================= Styles =================

    def _apply_styles(self):
        self.setStyleSheet(
            """
QMainWindow {
    background-color: #EEF2F7;
}

QDialog {
    background-color: #FFFFFF;
    color: #111827;
}

QMessageBox {
    background-color: #FFFFFF;
    color: #111827;
}

QMessageBox QLabel {
    color: #111827;
    background-color: transparent;
}

QFileDialog {
    background-color: #FFFFFF;
    color: #111827;
}

QFileDialog QLabel {
    color: #111827;
    background-color: transparent;
}

#TopBar {
    background-color: #FFFFFF;
    border-bottom: 1px solid #E2E8F0;
}

#LogoLabel {
    font-size: 28px;
    font-weight: 800;
    color: #A70064;
}

#HeaderTitle {
    font-size: 16px;
    font-weight: 700;
    color: #111827;
}

#HeaderSubtitle {
    font-size: 11px;
    color: #64748B;
}

#TopSearch {
    background-color: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 10px;
    padding: 8px 10px;
    color: #111827;
}

#TopSearch:focus {
    border: 1px solid #A70064;
}

#TopQuickBtn {
    background-color: #F3F4F6;
    color: #374151;
    border: 1px solid #E5E7EB;
    border-radius: 10px;
    padding: 8px 12px;
    font-weight: 600;
}

#TopQuickBtn:hover {
    background-color: #E5E7EB;
}

#NavShell {
    background-color: #0F172A;
    border-right: 1px solid #1E293B;
}

#NavTitle {
    color: #94A3B8;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    padding-left: 16px;
}

QListWidget#NavMenu {
    background-color: #0F172A;
    border: none;
    color: #94A3B8;
    font-size: 13px;
    padding-top: 2px;
}

QListWidget#NavMenu::item {
    padding: 12px 12px;
    border-left: 4px solid transparent;
}

QListWidget#NavMenu::item:hover {
    background-color: #1E293B;
    color: #FFFFFF;
}

QListWidget#NavMenu::item:selected {
    background-color: #111B31;
    color: #FFFFFF;
    border-left: 4px solid #A70064;
    font-weight: 600;
}

#WorkbenchShell {
    background-color: transparent;
}

QStackedWidget#WorkbenchStack {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 14px;
    padding: 8px;
}

#ContextPanel {
    background-color: #FFFFFF;
    border-left: 1px solid #E2E8F0;
}

#ContextTitle {
    color: #6B7280;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
}

#ContextModule {
    color: #111827;
    font-size: 18px;
    font-weight: 700;
}

#ContextDescription {
    color: #4B5563;
    font-size: 12px;
}

#ContextActionsTitle {
    color: #6B7280;
    font-size: 11px;
    font-weight: 700;
}

QPushButton#ContextActionButton {
    background-color: #F8FAFC;
    color: #334155;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 9px 10px;
    text-align: left;
    font-weight: 600;
}

QPushButton#ContextActionButton:hover {
    background-color: #EEF2FF;
    border: 1px solid #C7D2FE;
}

#HomeTitle {
    font-size: 24px;
    font-weight: 700;
    color: #111827;
}

#HomeSubtitle {
    font-size: 13px;
    color: #6B7280;
}

QPushButton#HomeActionCard {
    background-color: #FFFFFF;
    color: #111827;
    border: 1px solid #E5E7EB;
    border-radius: 14px;
    text-align: left;
    padding: 14px;
    font-weight: 600;
}

QPushButton#HomeActionCard:hover {
    background-color: #F8FAFC;
    border: 1px solid #D1D5DB;
}

QPushButton#HomeSecondaryButton {
    background-color: #F3F4F6;
    color: #334155;
    border: 1px solid #E5E7EB;
    border-radius: 10px;
    padding: 8px 12px;
    font-size: 12px;
    font-weight: 600;
}

QPushButton#HomeSecondaryButton:hover {
    background-color: #E5E7EB;
}

#MainCard {
    background-color: #FFFFFF;
    border-radius: 18px;
}

#Title {
    font-size: 24px;
    font-weight: 700;
    color: #111827;
}

#Subtitle {
    font-size: 13px;
    color: #6B7280;
}

#PrimaryButton {
    background-color: #A70064;
    color: #FFFFFF;
    border-radius: 12px;
    font-weight: 700;
    font-size: 14px;
}

#PrimaryButton:hover {
    background-color: #87004F;
}

#WorkflowBar {
    background-color: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
}

QPushButton#WorkflowStep {
    background-color: transparent;
    color: #475569;
    border: 1px solid transparent;
    border-radius: 9px;
    padding: 8px 10px;
    font-size: 12px;
    font-weight: 600;
}

QPushButton#WorkflowStep:hover {
    background-color: #EEF2FF;
    color: #111827;
}

QPushButton#WorkflowStep:checked {
    background-color: #A70064;
    color: #FFFFFF;
}

QFrame#PDFContextPanel {
    background-color: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
}

QToolButton#PDFInfoButton {
    background-color: #FFFFFF;
    color: #475569;
    border: 1px solid #CBD5E1;
    border-radius: 16px;
    min-width: 30px;
    max-width: 30px;
    min-height: 30px;
    max-height: 30px;
    font-weight: 700;
    font-size: 14px;
}

QToolButton#PDFInfoButton:hover {
    background-color: #EEF2FF;
    border: 1px solid #C7D2FE;
    color: #111827;
}

QToolButton#PDFInfoButton:checked {
    background-color: #A70064;
    border: 1px solid #A70064;
    color: #FFFFFF;
}

#PDFContextTitle {
    color: #6B7280;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
}

#PDFContextModule {
    color: #111827;
    font-size: 16px;
    font-weight: 700;
}

#PDFContextDesc,
#PDFContextTip {
    color: #475569;
    font-size: 12px;
}

QPushButton {
    background-color: #A70064;
    color: #FFFFFF;
    border: none;
    padding: 10px 18px;
    border-radius: 10px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #87004F;
}

QLineEdit,
QTextEdit,
QComboBox {
    background-color: #FFFFFF;
    color: #111827;
    border: 1px solid #E5E7EB;
    padding: 10px;
    border-radius: 10px;
}

QLineEdit:focus,
QTextEdit:focus,
QComboBox:focus {
    border: 1px solid #A70064;
}

QProgressBar {
    background-color: #F3F4F6;
    border-radius: 6px;
}

QProgressBar::chunk {
    background-color: #A70064;
    border-radius: 6px;
}

QScrollBar:vertical {
    background: transparent;
    width: 8px;
}

QScrollBar::handle:vertical {
    background: #CBD5E1;
    border-radius: 4px;
}

QStatusBar {
    background-color: #FFFFFF;
    color: #6B7280;
    border-top: 1px solid #E5E7EB;
}

#ModuleStack {
    border: 1px solid #E5E7EB;
    border-radius: 14px;
    background-color: #FFFFFF;
}
"""
        )
