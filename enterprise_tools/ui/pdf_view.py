"""
pdf_view.py - UI para el módulo PDF multifunción con flujo guiado
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QStackedWidget,
    QLabel,
    QPushButton,
    QFrame,
    QToolButton,
)

from ui.pdf_merge_preview import PDFMergePreview
from ui.pdf_split_preview import PDFSplitPreview
from ui.pdf_conversion_center_view import PDFConversionCenterView
from ui.pdf_decrypt_view import PDFDecryptView
from ui.pdf_viewer_view import PDFViewerView
from ui.pdf_compress_view import PDFCompressView


class PDFView(QWidget):
    def __init__(self):
        super().__init__()
        self.tools = [
            {
                "step": "Unir",
                "title": "Unir PDFs",
                "description": "Combina varios archivos PDF en un único documento final.",
                "tip": "Sugerencia: ordena los archivos en el orden final antes de unir.",
                "widget": PDFMergePreview(),
            },
            {
                "step": "Dividir",
                "title": "Dividir PDF",
                "description": "Separa páginas o rangos de un PDF en nuevos documentos.",
                "tip": "Sugerencia: define rangos claros para evitar cortes incompletos.",
                "widget": PDFSplitPreview(),
            },
            {
                "step": "Convertir+",
                "title": "Centro de conversiones",
                "description": "Convierte entre PDF, imágenes (ida y vuelta), Office, TXT y HTML desde un solo flujo.",
                "tip": "Sugerencia: aquí están incluidas PDF→IMG e IMG→PDF con selección múltiple de imágenes.",
                "widget": PDFConversionCenterView(),
            },
            {
                "step": "Desencriptar",
                "title": "Desencriptar PDF",
                "description": "Quita restricción de contraseña cuando se dispone de acceso válido.",
                "tip": "Sugerencia: guarda una copia del original antes del proceso.",
                "widget": PDFDecryptView(),
            },
            {
                "step": "Visualizar",
                "title": "Visualizador PDF",
                "description": "Abre y revisa documentos PDF dentro de la suite.",
                "tip": "Sugerencia: usa visualización para validar el resultado final.",
                "widget": PDFViewerView(),
            },
            {
                "step": "Comprimir",
                "title": "Comprimir PDF/Imagen (KB/MB)",
                "description": "Reduce tamaño de PDF o imágenes con unidad configurable (KB o MB).",
                "tip": "Sugerencia: usa MB para límites grandes y KB para cargas estrictas.",
                "widget": PDFCompressView(),
            },
        ]
        self.step_buttons = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        title = QLabel("Herramientas PDF")
        title.setObjectName("Title")

        subtitle = QLabel("Flujo guiado: selecciona un paso y trabaja en el panel principal")
        subtitle.setObjectName("Subtitle")
        subtitle.setWordWrap(True)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        title_layout = QVBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(2)
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)

        self.info_toggle = QToolButton()
        self.info_toggle.setObjectName("PDFInfoButton")
        self.info_toggle.setText("ℹ")
        self.info_toggle.setCheckable(True)
        self.info_toggle.setToolTip("Mostrar asistente de paso")
        self.info_toggle.toggled.connect(self._toggle_step_assistant)

        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        header_layout.addWidget(self.info_toggle)

        workflow_bar = QFrame()
        workflow_bar.setObjectName("WorkflowBar")
        workflow_layout = QHBoxLayout()
        workflow_layout.setContentsMargins(8, 8, 8, 8)
        workflow_layout.setSpacing(6)

        for index, tool in enumerate(self.tools):
            button = QPushButton(f"{index + 1}. {tool['step']}")
            button.setObjectName("WorkflowStep")
            button.setCheckable(True)
            button.clicked.connect(lambda _, idx=index: self._change_tool(idx))
            self.step_buttons.append(button)
            workflow_layout.addWidget(button)

        workflow_bar.setLayout(workflow_layout)

        body_layout = QHBoxLayout()
        body_layout.setSpacing(12)

        self.stack = QStackedWidget()
        self.stack.setObjectName("ModuleStack")
        for tool in self.tools:
            self.stack.addWidget(tool["widget"])

        self.step_assistant = QFrame()
        self.step_assistant.setObjectName("PDFContextPanel")
        self.step_assistant.setVisible(False)

        context_layout = QVBoxLayout()
        context_layout.setContentsMargins(14, 14, 14, 14)
        context_layout.setSpacing(8)

        context_title = QLabel("ASISTENTE DE PASO")
        context_title.setObjectName("PDFContextTitle")

        self.current_tool_title = QLabel("-")
        self.current_tool_title.setObjectName("PDFContextModule")
        self.current_tool_title.setWordWrap(True)

        self.current_tool_desc = QLabel("-")
        self.current_tool_desc.setObjectName("PDFContextDesc")
        self.current_tool_desc.setWordWrap(True)

        self.current_tool_tip = QLabel("-")
        self.current_tool_tip.setObjectName("PDFContextTip")
        self.current_tool_tip.setWordWrap(True)

        context_layout.addWidget(context_title)
        context_layout.addWidget(self.current_tool_title)
        context_layout.addWidget(self.current_tool_desc)
        context_layout.addSpacing(4)
        context_layout.addWidget(self.current_tool_tip)
        self.step_assistant.setLayout(context_layout)

        body_layout.addWidget(self.stack, 1)

        layout.addLayout(header_layout)
        layout.addWidget(workflow_bar)
        layout.addWidget(self.step_assistant)
        layout.addLayout(body_layout)

        self.setLayout(layout)
        self._change_tool(0)

    def _toggle_step_assistant(self, visible):
        self.step_assistant.setVisible(bool(visible))
        if visible:
            self.info_toggle.setText("✕")
            self.info_toggle.setToolTip("Ocultar asistente de paso")
        else:
            self.info_toggle.setText("ℹ")
            self.info_toggle.setToolTip("Mostrar asistente de paso")

    def _change_tool(self, index):
        if not (0 <= index < len(self.tools)):
            return

        self.stack.setCurrentIndex(index)

        for current_index, button in enumerate(self.step_buttons):
            button.blockSignals(True)
            button.setChecked(current_index == index)
            button.blockSignals(False)

        current_tool = self.tools[index]
        self.current_tool_title.setText(current_tool["title"])
        self.current_tool_desc.setText(current_tool["description"])
        self.current_tool_tip.setText(current_tool["tip"])
