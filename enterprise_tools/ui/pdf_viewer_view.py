"""
pdf_viewer_view.py - Vista para visualizar y editar PDFs dentro de la app
Selección directa por mouse para subrayar texto y firma visible por imagen.
"""

import os
from datetime import datetime

from PySide6.QtCore import Qt, QRect, Signal, QBuffer, QIODevice, QEvent, QTimer
from PySide6.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QBrush, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QScrollArea,
    QComboBox,
    QFrame,
    QDialog,
    QSizePolicy,
    QTabWidget,
    QSplitter,
)

from utils.app_paths import get_output_dir
from utils.drag_drop import extract_dropped_paths, filter_existing_files

try:
    import fitz  # PyMuPDF
    PDF_EDITOR_AVAILABLE = True
except Exception:
    PDF_EDITOR_AVAILABLE = False


class SignaturePadCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(560, 220)
        self.setAttribute(Qt.WA_StaticContents)
        self.setAttribute(Qt.WA_AcceptTouchEvents, True)
        self.last_point = None
        self.touch_active = False
        self.has_strokes = False
        self.pen_color = QColor(17, 24, 39)
        self.pen_width = 4
        self.canvas = QImage(self.size(), QImage.Format_ARGB32)
        self.canvas.fill(Qt.transparent)
        self.setAutoFillBackground(False)
        self.setStyleSheet("background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 8px;")

    def event(self, event):
        event_type = event.type()
        if event_type in (QEvent.TouchBegin, QEvent.TouchUpdate, QEvent.TouchEnd, QEvent.TouchCancel):
            points = event.points() if hasattr(event, "points") else []

            if event_type in (QEvent.TouchEnd, QEvent.TouchCancel):
                if self.last_point is not None and points:
                    current_point = points[0].position().toPoint()
                    self._draw_line(self.last_point, current_point)
                self.last_point = None
                self.touch_active = False
                event.accept()
                return True

            if not points:
                event.accept()
                return True

            current_point = points[0].position().toPoint()
            self.touch_active = True

            if event_type == QEvent.TouchBegin:
                self.last_point = current_point
            elif event_type == QEvent.TouchUpdate:
                if self.last_point is None:
                    self.last_point = current_point
                else:
                    self._draw_line(self.last_point, current_point)
                    self.last_point = current_point

            event.accept()
            return True

        return super().event(event)

    def resizeEvent(self, event):
        if self.width() > self.canvas.width() or self.height() > self.canvas.height():
            new_canvas = QImage(self.size(), QImage.Format_ARGB32)
            new_canvas.fill(Qt.transparent)
            painter = QPainter(new_canvas)
            painter.drawImage(0, 0, self.canvas)
            painter.end()
            self.canvas = new_canvas
        super().resizeEvent(event)

    def _draw_line(self, start_point, end_point):
        painter = QPainter(self.canvas)
        painter.setRenderHint(QPainter.Antialiasing, True)
        pen = QPen(self.pen_color, self.pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(start_point, end_point)
        painter.end()
        self.has_strokes = True
        self.update()

    def clear_canvas(self):
        self.canvas.fill(Qt.transparent)
        self.has_strokes = False
        self.last_point = None
        self.touch_active = False
        self.update()

    def mousePressEvent(self, event):
        if self.touch_active:
            event.accept()
            return
        if event.button() == Qt.LeftButton:
            self.last_point = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.touch_active:
            event.accept()
            return
        if self.last_point is not None and (event.buttons() & Qt.LeftButton):
            current_point = event.position().toPoint()
            self._draw_line(self.last_point, current_point)
            self.last_point = current_point
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.touch_active:
            event.accept()
            return
        if event.button() == Qt.LeftButton and self.last_point is not None:
            current_point = event.position().toPoint()
            self._draw_line(self.last_point, current_point)
            self.last_point = None
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#FFFFFF"))
        painter.drawImage(0, 0, self.canvas)
        painter.setPen(QPen(QColor("#CBD5E1"), 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        painter.end()

    def _content_rect(self):
        width = self.canvas.width()
        height = self.canvas.height()
        min_x, min_y = width, height
        max_x, max_y = -1, -1

        for y in range(height):
            for x in range(width):
                if QColor.fromRgba(self.canvas.pixel(x, y)).alpha() > 0:
                    min_x = min(min_x, x)
                    min_y = min(min_y, y)
                    max_x = max(max_x, x)
                    max_y = max(max_y, y)

        if max_x < min_x or max_y < min_y:
            return None

        margin = 8
        min_x = max(0, min_x - margin)
        min_y = max(0, min_y - margin)
        max_x = min(width - 1, max_x + margin)
        max_y = min(height - 1, max_y + margin)
        return QRect(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)

    def get_signature_pixmap(self):
        if not self.has_strokes:
            return None

        content_rect = self._content_rect()
        if content_rect is None:
            return None

        cropped = self.canvas.copy(content_rect)
        return QPixmap.fromImage(cropped)


class SignaturePadDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.signature_pixmap = None
        self.setWindowTitle("Capturar firma con touch")
        self.resize(700, 360)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        self.setStyleSheet("QDialog { background-color: #F8FAFC; }")

        info = QLabel("Firma en el recuadro con touch, mouse o lápiz. Luego pulsa 'Usar firma'.")
        info.setStyleSheet("color: #334155;")
        layout.addWidget(info)

        self.canvas = SignaturePadCanvas()
        layout.addWidget(self.canvas, 1)

        actions = QHBoxLayout()
        self.btn_clear = QPushButton("Limpiar")
        self.btn_clear.clicked.connect(self.canvas.clear_canvas)
        self.btn_use = QPushButton("Usar firma")
        self.btn_use.clicked.connect(self._accept_signature)
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)

        actions.addStretch()
        actions.addWidget(self.btn_clear)
        actions.addWidget(self.btn_use)
        actions.addWidget(self.btn_cancel)

        layout.addLayout(actions)
        self.setLayout(layout)

    def _accept_signature(self):
        pixmap = self.canvas.get_signature_pixmap()
        if pixmap is None or pixmap.isNull():
            QMessageBox.warning(self, "Firma vacía", "Dibuja la firma antes de continuar.")
            return
        self.signature_pixmap = pixmap
        self.accept()


class SelectablePageLabel(QLabel):
    selectionChanged = Signal(object)
    signatureMoved = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_AcceptTouchEvents, True)
        self.start_point = None
        self.end_point = None
        self.saved_rects = []
        self.active_color = QColor(255, 220, 60, 90)
        self.signature_pixmap = None
        self.signature_rect = None
        self.dragging_signature = False
        self.drag_offset = None
        self.touch_active = False
        self._ignore_mouse_events = False

    def set_overlay_color(self, color):
        self.active_color = color
        self.update()

    def clear_saved_rects(self):
        self.saved_rects = []
        self.update()

    def set_saved_rects(self, rects):
        self.saved_rects = list(rects)
        self.update()

    def set_signature_preview(self, pixmap, rect):
        self.signature_pixmap = pixmap
        self.signature_rect = rect.normalized() if rect else None
        self.update()

    def clear_signature_preview(self):
        self.signature_pixmap = None
        self.signature_rect = None
        self.dragging_signature = False
        self.drag_offset = None
        self.update()

    def _clamp_signature_rect(self, rect):
        if rect is None:
            return None

        width = max(1, rect.width())
        height = max(1, rect.height())

        max_x = max(0, self.width() - width)
        max_y = max(0, self.height() - height)

        clamped_x = min(max(rect.x(), 0), max_x)
        clamped_y = min(max(rect.y(), 0), max_y)
        return QRect(clamped_x, clamped_y, width, height)

    def _clear_touch_mouse_guard(self):
        self._ignore_mouse_events = False

    def event(self, event):
        event_type = event.type()
        if event_type in (QEvent.TouchBegin, QEvent.TouchUpdate, QEvent.TouchEnd, QEvent.TouchCancel):
            points = event.points() if hasattr(event, "points") else []
            current_point = points[0].position().toPoint() if points else None

            if event_type == QEvent.TouchBegin:
                self.touch_active = True
                self._ignore_mouse_events = True

                if current_point is not None and self.signature_rect is not None and self.signature_rect.contains(current_point):
                    self.dragging_signature = True
                    self.drag_offset = current_point - self.signature_rect.topLeft()
                    self.start_point = None
                    self.end_point = None
                else:
                    self.dragging_signature = False
                    self.drag_offset = None
                    self.start_point = current_point
                    self.end_point = current_point
                    self.update()

                event.accept()
                return True

            if event_type == QEvent.TouchUpdate:
                if current_point is not None and self.dragging_signature and self.signature_rect is not None and self.drag_offset is not None:
                    top_left = current_point - self.drag_offset
                    moved_rect = QRect(top_left, self.signature_rect.size())
                    self.signature_rect = self._clamp_signature_rect(moved_rect)
                    self.signatureMoved.emit(self.signature_rect)
                    self.update()
                elif current_point is not None and self.start_point is not None:
                    self.end_point = current_point
                    self.update()

                event.accept()
                return True

            if event_type in (QEvent.TouchEnd, QEvent.TouchCancel):
                if self.dragging_signature:
                    self.dragging_signature = False
                    if self.signature_rect is not None:
                        self.signatureMoved.emit(self.signature_rect)
                    self.update()
                elif self.start_point is not None:
                    final_point = self.end_point if self.end_point is not None else self.start_point
                    rect = QRect(self.start_point, final_point).normalized()
                    self.selectionChanged.emit(rect)
                    self.start_point = None
                    self.end_point = None
                    self.update()

                self.touch_active = False
                self.drag_offset = None
                QTimer.singleShot(180, self._clear_touch_mouse_guard)
                event.accept()
                return True

        return super().event(event)

    def mousePressEvent(self, event):
        if self.touch_active or self._ignore_mouse_events:
            event.accept()
            return

        if event.button() == Qt.LeftButton and self.signature_rect is not None:
            current_point = event.position().toPoint()
            if self.signature_rect.contains(current_point):
                self.dragging_signature = True
                self.drag_offset = current_point - self.signature_rect.topLeft()
                return

        if event.button() == Qt.LeftButton:
            self.start_point = event.position().toPoint()
            self.end_point = self.start_point
            self.update()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.touch_active or self._ignore_mouse_events:
            event.accept()
            return

        if self.dragging_signature and self.signature_rect is not None:
            current_point = event.position().toPoint()
            top_left = current_point - self.drag_offset
            moved_rect = QRect(top_left, self.signature_rect.size())
            self.signature_rect = self._clamp_signature_rect(moved_rect)
            self.signatureMoved.emit(self.signature_rect)
            self.update()
            return

        if self.start_point is not None:
            self.end_point = event.position().toPoint()
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.touch_active or self._ignore_mouse_events:
            event.accept()
            return

        if self.dragging_signature and event.button() == Qt.LeftButton:
            self.dragging_signature = False
            if self.signature_rect is not None:
                self.signatureMoved.emit(self.signature_rect)
            self.update()
            return

        if self.start_point is not None and event.button() == Qt.LeftButton:
            self.end_point = event.position().toPoint()
            rect = QRect(self.start_point, self.end_point).normalized()
            self.selectionChanged.emit(rect)
            self.start_point = None
            self.end_point = None
            self.update()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)

        if self.start_point is not None and self.end_point is not None:
            dragging_rect = QRect(self.start_point, self.end_point).normalized()
            painter.setPen(QPen(QColor(220, 38, 38), 2, Qt.DashLine))
            painter.setBrush(QBrush(self.active_color))
            painter.drawRect(dragging_rect)

        for rect_info in self.saved_rects:
            if isinstance(rect_info, tuple):
                rect, color = rect_info
            else:
                rect = rect_info
                color = QColor(255, 220, 60, 90)

            painter.setPen(QPen(QColor(161, 98, 7), 1, Qt.SolidLine))
            painter.setBrush(QBrush(color))
            painter.drawRect(rect)

        if self.signature_pixmap is not None and self.signature_rect is not None:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(255, 255, 255, 210))
            painter.drawRect(self.signature_rect)
            preview_pixmap = self.signature_pixmap.scaled(
                self.signature_rect.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            draw_x = self.signature_rect.x() + (self.signature_rect.width() - preview_pixmap.width()) // 2
            draw_y = self.signature_rect.y() + (self.signature_rect.height() - preview_pixmap.height()) // 2
            painter.drawPixmap(draw_x, draw_y, preview_pixmap)
            painter.setPen(QPen(QColor(167, 0, 100), 2, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(self.signature_rect)


class PDFViewerView(QWidget):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.current_file = None
        self.signature_image_path = None
        self.signature_image_bytes = None
        self.signature_preview_pixmap = None
        self.signature_preview_pdf_rect = None
        self.signature_preview_page = None
        self.current_page = 0
        self.total_pages = 0
        self.zoom_factor = 1.0
        self.doc = None
        self.current_page_size = (1, 1)
        self.pending_pdf_rects = []
        self._auto_fit_on_resize = True
        self._fit_padding = 12
        self._fit_boost = 1.10
        self._splitter_user_adjusted = False
        self._default_viewer_width_ratio = 0.78
        self._min_tools_width = 220
        self._max_tools_width = 420
        self._undo_stack = []
        self._redo_stack = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        self.title = QLabel("Editor básico de PDF")
        self.title.setObjectName("ViewerTitle")
        self.status_label = QLabel("Selecciona un PDF y arrastra: la selección se colorea al instante.")
        self.status_label.setObjectName("ViewerStatus")

        self.btn_open = QPushButton("Abrir PDF")
        self.btn_open.setObjectName("RibbonPrimaryButton")
        self.btn_open.setFixedHeight(32)
        self.btn_open.clicked.connect(self._open_pdf)

        toolbar = QFrame()
        toolbar.setObjectName("ViewerToolbar")
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(12, 8, 12, 8)
        toolbar_layout.setSpacing(8)

        toolbar_layout.addWidget(QLabel("Archivo:"))
        toolbar_layout.addWidget(self.btn_open)

        self.btn_prev = QPushButton("◀ Anterior")
        self.btn_prev.setObjectName("RibbonGhostButton")
        self.btn_prev.setFixedHeight(32)
        self.btn_prev.clicked.connect(self._prev_page)

        self.btn_next = QPushButton("Siguiente ▶")
        self.btn_next.setObjectName("RibbonGhostButton")
        self.btn_next.setFixedHeight(32)
        self.btn_next.clicked.connect(self._next_page)

        self.page_input = QLineEdit()
        self.page_input.setPlaceholderText("Página")
        self.page_input.setFixedWidth(78)
        self.page_input.setFixedHeight(32)

        self.btn_go = QPushButton("Ir")
        self.btn_go.setObjectName("RibbonPrimaryButton")
        self.btn_go.setFixedHeight(32)
        self.btn_go.setFixedWidth(46)
        self.btn_go.clicked.connect(self._go_to_page)

        self.page_count_label = QLabel("/ 0")

        self.btn_zoom_out = QPushButton("-")
        self.btn_zoom_out.setObjectName("RibbonGhostButton")
        self.btn_zoom_out.setFixedSize(38, 32)
        self.btn_zoom_out.clicked.connect(self._zoom_out)

        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_in.setObjectName("RibbonGhostButton")
        self.btn_zoom_in.setFixedSize(38, 32)
        self.btn_zoom_in.clicked.connect(self._zoom_in)

        self.btn_zoom_reset = QPushButton("100%")
        self.btn_zoom_reset.setObjectName("RibbonGhostButton")
        self.btn_zoom_reset.setFixedSize(62, 32)
        self.btn_zoom_reset.clicked.connect(self._zoom_reset)

        self.btn_undo = QPushButton("↩ Deshacer")
        self.btn_undo.setObjectName("RibbonGhostButton")
        self.btn_undo.setFixedHeight(32)
        self.btn_undo.setToolTip("Deshacer última acción (Ctrl+Z)")
        self.btn_undo.setEnabled(False)
        self.btn_undo.clicked.connect(self._undo_action)

        self.btn_redo = QPushButton("↪ Rehacer")
        self.btn_redo.setObjectName("RibbonGhostButton")
        self.btn_redo.setFixedHeight(32)
        self.btn_redo.setToolTip("Rehacer acción (Ctrl+Y)")
        self.btn_redo.setEnabled(False)
        self.btn_redo.clicked.connect(self._redo_action)

        toolbar_layout.addSpacing(8)
        toolbar_layout.addWidget(QLabel("Navegación:"))
        toolbar_layout.addWidget(self.btn_prev)
        toolbar_layout.addWidget(self.btn_next)
        toolbar_layout.addWidget(self.page_input)
        toolbar_layout.addWidget(self.btn_go)
        toolbar_layout.addWidget(self.page_count_label)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(QLabel("Zoom:"))
        toolbar_layout.addWidget(self.btn_zoom_out)
        toolbar_layout.addWidget(self.btn_zoom_in)
        toolbar_layout.addWidget(self.btn_zoom_reset)
        toolbar_layout.addSpacing(8)
        toolbar_layout.addWidget(QLabel("Historial:"))
        toolbar_layout.addWidget(self.btn_undo)
        toolbar_layout.addWidget(self.btn_redo)
        toolbar.setLayout(toolbar_layout)

        layout.addWidget(self.title)
        layout.addWidget(self.status_label)
        layout.addWidget(toolbar)

        self.tools_tabs = QTabWidget()
        self.tools_tabs.setObjectName("ViewerToolsTabs")

        underline_tab = QWidget()
        underline_layout = QVBoxLayout()
        underline_layout.setContentsMargins(10, 10, 10, 10)
        underline_layout.setSpacing(10)

        self.underline_page_input = QSpinBox()
        self.underline_page_input.setMinimum(1)
        self.underline_page_input.setMaximum(1)
        self.underline_page_input.setPrefix("Pág. ")
        self.underline_page_input.setFixedHeight(34)

        self.underline_color_combo = QComboBox()
        self.underline_color_combo.addItems(["Amarillo", "Verde", "Rosa", "Azul"])
        self.underline_color_combo.currentIndexChanged.connect(self._update_selection_color)
        self.underline_color_combo.setFixedHeight(34)

        self.btn_underline = QPushButton("Aplicar subrayados")
        self.btn_underline.setObjectName("RibbonPrimaryButton")
        self.btn_underline.setFixedHeight(34)
        self.btn_underline.clicked.connect(self._underline_selection)

        self.btn_clear_selection = QPushButton("Limpiar selecciones")
        self.btn_clear_selection.setObjectName("RibbonGhostButton")
        self.btn_clear_selection.setFixedHeight(34)
        self.btn_clear_selection.clicked.connect(self._clear_pending_selections)

        underline_layout.addWidget(QLabel("Página para subrayar"))
        underline_layout.addWidget(self.underline_page_input)
        underline_layout.addWidget(QLabel("Color"))
        underline_layout.addWidget(self.underline_color_combo)
        underline_layout.addWidget(self.btn_underline)
        underline_layout.addWidget(self.btn_clear_selection)
        underline_layout.addStretch()
        underline_tab.setLayout(underline_layout)

        signature_tab = QWidget()
        signature_layout = QVBoxLayout()
        signature_layout.setContentsMargins(10, 10, 10, 10)
        signature_layout.setSpacing(10)

        self.btn_select_signature = QPushButton("Seleccionar firma (imagen)")
        self.btn_select_signature.setObjectName("RibbonGhostButton")
        self.btn_select_signature.setFixedHeight(34)
        self.btn_select_signature.clicked.connect(self._select_signature_image)

        self.btn_draw_signature = QPushButton("Firmar con touch")
        self.btn_draw_signature.setObjectName("RibbonGhostButton")
        self.btn_draw_signature.setFixedHeight(34)
        self.btn_draw_signature.clicked.connect(self._open_signature_pad)

        self.btn_place_signature = QPushButton("Colocar firma")
        self.btn_place_signature.setObjectName("RibbonGhostButton")
        self.btn_place_signature.setFixedHeight(34)
        self.btn_place_signature.clicked.connect(self._place_signature_preview)

        self.signature_page_input = QSpinBox()
        self.signature_page_input.setMinimum(1)
        self.signature_page_input.setMaximum(1)
        self.signature_page_input.setPrefix("Pág. ")
        self.signature_page_input.setFixedHeight(34)

        self.btn_sign = QPushButton("Guardar firma en PDF")
        self.btn_sign.setObjectName("RibbonPrimaryButton")
        self.btn_sign.clicked.connect(self._insert_signature)
        self.btn_sign.setFixedHeight(34)

        signature_layout.addWidget(self.btn_select_signature)
        signature_layout.addWidget(self.btn_draw_signature)
        signature_layout.addWidget(self.btn_place_signature)
        signature_layout.addWidget(QLabel("Página de firma"))
        signature_layout.addWidget(self.signature_page_input)
        signature_layout.addWidget(self.btn_sign)
        signature_layout.addStretch()
        signature_tab.setLayout(signature_layout)

        self.tools_tabs.addTab(underline_tab, "Subrayado")
        self.tools_tabs.addTab(signature_tab, "Firma")

        self.edit_note = QLabel("Nota: firma visible (imagen), no firma criptográfica con certificado digital.")
        self.edit_note.setObjectName("ViewerNote")

        tools_panel = QFrame()
        tools_panel.setObjectName("ViewerToolsPanel")
        tools_panel.setMinimumWidth(self._min_tools_width)
        tools_panel.setMaximumWidth(self._max_tools_width)
        tools_layout = QVBoxLayout()
        tools_layout.setContentsMargins(10, 10, 10, 10)
        tools_layout.setSpacing(8)
        tools_layout.addWidget(QLabel("Herramientas"))
        tools_layout.addWidget(self.tools_tabs, 1)
        tools_layout.addWidget(self.edit_note)
        tools_panel.setLayout(tools_layout)

        reader_panel = QFrame()
        reader_panel.setObjectName("ViewerReaderPanel")
        reader_layout = QVBoxLayout()
        reader_layout.setContentsMargins(8, 8, 8, 8)
        reader_layout.setSpacing(6)

        if PDF_EDITOR_AVAILABLE:
            self.page_label = SelectablePageLabel()
            self.page_label.setAlignment(Qt.AlignCenter)
            self.page_label.selectionChanged.connect(self._on_selection_changed)
            self.page_label.signatureMoved.connect(self._on_signature_preview_moved)
            self._update_selection_color()

            self.scroll_area = QScrollArea()
            self.scroll_area.setWidgetResizable(False)
            self.scroll_area.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
            self.scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.scroll_area.setWidget(self.page_label)
            self.scroll_area.setMinimumHeight(440)

            reader_layout.addWidget(self.scroll_area, 1)
            reader_panel.setLayout(reader_layout)

            self.viewer_splitter = QSplitter(Qt.Horizontal)
            self.viewer_splitter.setObjectName("ViewerSplitter")
            self.viewer_splitter.setChildrenCollapsible(False)
            self.viewer_splitter.addWidget(tools_panel)
            self.viewer_splitter.addWidget(reader_panel)
            self.viewer_splitter.setStretchFactor(0, 0)
            self.viewer_splitter.setStretchFactor(1, 1)
            self.viewer_splitter.splitterMoved.connect(self._on_viewer_splitter_moved)

            layout.addWidget(self.viewer_splitter, 1)
            self._apply_default_splitter_sizes()
        else:
            warning = QLabel("No está disponible PyMuPDF en este entorno para visualizar/editar PDF.")
            warning.setWordWrap(True)
            warning.setStyleSheet("color: #B91C1C;")
            reader_layout.addWidget(warning)
            reader_panel.setLayout(reader_layout)

            layout.addWidget(tools_panel)
            layout.addWidget(reader_panel, 1)

        self.setLayout(layout)
        self._apply_view_styles()

        self.undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        self.undo_shortcut.setContext(Qt.WidgetWithChildrenShortcut)
        self.undo_shortcut.activated.connect(self._handle_undo_shortcut)

        self.redo_shortcut = QShortcut(QKeySequence("Ctrl+Y"), self)
        self.redo_shortcut.setContext(Qt.WidgetWithChildrenShortcut)
        self.redo_shortcut.activated.connect(self._handle_redo_shortcut)

        self._standard_shortcuts = []
        self._bind_standard_shortcut("Ctrl+C", self._copy_on_focused_widget)
        self._bind_standard_shortcut("Ctrl+V", self._paste_on_focused_widget)
        self._bind_standard_shortcut("Ctrl+X", self._cut_on_focused_widget)
        self._bind_standard_shortcut("Ctrl+A", self._select_all_on_focused_widget)

        self._set_controls_enabled(False)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_default_splitter_sizes()
        if self._auto_fit_on_resize and self.doc is not None and self.total_pages > 0:
            QTimer.singleShot(0, self._fit_current_page_to_viewport)

    def _on_viewer_splitter_moved(self, pos, index):
        self._splitter_user_adjusted = True

    def _apply_default_splitter_sizes(self):
        if self._splitter_user_adjusted or not hasattr(self, "viewer_splitter"):
            return

        splitter_width = self.viewer_splitter.width()
        if splitter_width <= 0:
            return

        viewer_width = int(splitter_width * self._default_viewer_width_ratio)
        min_viewer_width = int(splitter_width * 0.70)
        viewer_width = max(viewer_width, min_viewer_width)
        viewer_width = min(viewer_width, max(1, splitter_width - self._min_tools_width))

        tools_width = splitter_width - viewer_width
        tools_width = max(self._min_tools_width, min(self._max_tools_width, tools_width))
        viewer_width = max(1, splitter_width - tools_width)
        self.viewer_splitter.setSizes([tools_width, viewer_width])

    def _apply_view_styles(self):
        self.setStyleSheet("""
        #ViewerTitle {
            font-size: 22px;
            font-weight: 700;
            color: #111827;
        }
        #ViewerStatus {
            color: #475569;
            font-size: 13px;
        }
        #ViewerToolbar {
            background-color: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 10px;
        }
        #ViewerToolbar QLabel {
            color: #334155;
            font-weight: 600;
        }
        #ViewerToolsPanel {
            background-color: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 10px;
        }
        #ViewerToolsPanel QLabel {
            color: #0F172A;
            font-weight: 700;
        }
        #ViewerReaderPanel {
            background-color: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 10px;
        }
        #ViewerNote {
            color: #64748B;
            font-size: 12px;
            font-weight: 400;
        }
        #ViewerSplitter::handle {
            background-color: #CBD5E1;
            width: 6px;
            margin: 0 4px;
            border-radius: 3px;
        }
        #ViewerToolsTabs::pane {
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            background-color: #F8FAFC;
        }
        #ViewerToolsTabs QTabBar::tab {
            background-color: #E2E8F0;
            color: #475569;
            border: 1px solid #CBD5E1;
            border-bottom: none;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            padding: 7px 12px;
            margin-right: 4px;
            font-weight: 700;
        }
        #ViewerToolsTabs QTabBar::tab:selected {
            background-color: #FFFFFF;
            color: #111827;
            border-color: #A70064;
        }
        #ViewerToolsTabs QTabBar::tab:hover {
            color: #1E293B;
        }
        #RibbonPrimaryButton {
            background-color: #A70064;
            color: #FFFFFF;
            border: none;
            border-radius: 8px;
            padding: 6px 10px;
            font-weight: 700;
        }
        #RibbonPrimaryButton:hover {
            background-color: #87004F;
        }
        #RibbonGhostButton {
            background-color: #FFFFFF;
            color: #334155;
            border: 1px solid #CBD5E1;
            border-radius: 8px;
            padding: 6px 10px;
            font-weight: 600;
        }
        #RibbonGhostButton:hover {
            background-color: #F1F5F9;
            border: 1px solid #94A3B8;
        }
        """)

    def _set_controls_enabled(self, enabled):
        self.btn_prev.setEnabled(enabled)
        self.btn_next.setEnabled(enabled)
        self.page_input.setEnabled(enabled)
        self.btn_go.setEnabled(enabled)
        self.btn_zoom_out.setEnabled(enabled)
        self.btn_zoom_in.setEnabled(enabled)
        self.btn_zoom_reset.setEnabled(enabled)
        self.underline_page_input.setEnabled(enabled and PDF_EDITOR_AVAILABLE)
        self.underline_color_combo.setEnabled(enabled and PDF_EDITOR_AVAILABLE)
        self.btn_underline.setEnabled(enabled and PDF_EDITOR_AVAILABLE)
        self.btn_clear_selection.setEnabled(enabled and PDF_EDITOR_AVAILABLE)
        self.btn_select_signature.setEnabled(enabled and PDF_EDITOR_AVAILABLE)
        self.btn_draw_signature.setEnabled(enabled and PDF_EDITOR_AVAILABLE)
        self.btn_place_signature.setEnabled(enabled and PDF_EDITOR_AVAILABLE)
        self.signature_page_input.setEnabled(enabled and PDF_EDITOR_AVAILABLE)
        self.btn_sign.setEnabled(enabled and PDF_EDITOR_AVAILABLE)
        self._update_undo_redo_buttons()

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
        if dropped_pdfs and PDF_EDITOR_AVAILABLE:
            self._load_pdf_file(dropped_pdfs[0])
            event.acceptProposedAction()
            return
        event.ignore()

    def _open_pdf(self):
        if not PDF_EDITOR_AVAILABLE:
            QMessageBox.warning(self, "No disponible", "PyMuPDF no está disponible en este entorno.")
            return

        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar PDF", "", "Archivos PDF (*.pdf)")
        if not file_path:
            return

        self._load_pdf_file(file_path)

    def _load_pdf_file(self, file_path):
        if self.doc is not None:
            self.doc.close()

        self.doc = fitz.open(file_path)
        self.current_file = file_path
        self.current_page = 0
        self.total_pages = len(self.doc)
        self.pending_pdf_rects = []
        self.signature_preview_pdf_rect = None
        self.signature_preview_page = None
        self.page_count_label.setText(f"/ {self.total_pages}")
        self.page_input.setText("1")
        self.status_label.setText(f"Archivo abierto: {file_path}")
        self.underline_page_input.setMaximum(max(1, self.total_pages))
        self.signature_page_input.setMaximum(max(1, self.total_pages))
        self._auto_fit_on_resize = True
        self._set_controls_enabled(self.total_pages > 0)
        self._render_current_page()
        QTimer.singleShot(0, self._fit_current_page_to_viewport)

    def _render_current_page(self):
        if not PDF_EDITOR_AVAILABLE or not self.doc or self.total_pages <= 0:
            return

        page = self.doc[self.current_page]
        self.current_page_size = (float(page.rect.width), float(page.rect.height))
        matrix = fitz.Matrix(self.zoom_factor, self.zoom_factor)
        pix = page.get_pixmap(matrix=matrix, alpha=False)

        image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
        self.page_label.setPixmap(QPixmap.fromImage(image.copy()))
        self.page_label.setFixedSize(pix.width, pix.height)

        self.page_input.setText(str(self.current_page + 1))
        self.underline_page_input.setValue(self.current_page + 1)
        if self.signature_preview_page is None:
            self.signature_page_input.setValue(self.current_page + 1)
        self._sync_overlay_from_pending_rects()
        self._sync_signature_preview_overlay()

    def _jump_to_page(self, page_index):
        if not self.doc or self.total_pages <= 0:
            return
        page_index = max(0, min(page_index, self.total_pages - 1))
        self.current_page = page_index
        self.pending_pdf_rects = []
        self.page_label.clear_saved_rects()
        self._render_current_page()
        if self._auto_fit_on_resize:
            QTimer.singleShot(0, self._fit_current_page_to_viewport)

    def _prev_page(self):
        self._jump_to_page(self.current_page - 1)

    def _next_page(self):
        self._jump_to_page(self.current_page + 1)

    def _go_to_page(self):
        if self.total_pages <= 0:
            return
        try:
            requested = int(self.page_input.text().strip())
            self._jump_to_page(requested - 1)
        except ValueError:
            QMessageBox.warning(self, "Página inválida", "Ingresa un número de página válido.")

    def _zoom_in(self):
        self._auto_fit_on_resize = False
        self.zoom_factor = min(self.zoom_factor + 0.15, 4.0)
        self._render_current_page()

    def _zoom_out(self):
        self._auto_fit_on_resize = False
        self.zoom_factor = max(self.zoom_factor - 0.15, 0.3)
        self._render_current_page()

    def _zoom_reset(self):
        self._auto_fit_on_resize = True
        self._fit_current_page_to_viewport()

    def _on_selection_changed(self, rect):
        selection_pdf_rect = self._selection_to_pdf_rect(rect)
        if selection_pdf_rect is None:
            return
        self._push_undo()
        color_name = self.underline_color_combo.currentText()
        self.pending_pdf_rects.append((selection_pdf_rect, color_name))
        self._sync_overlay_from_pending_rects()
        self.status_label.setText(f"Selecciones pendientes: {len(self.pending_pdf_rects)}")

    def _update_selection_color(self):
        if not hasattr(self, "page_label"):
            return
        color_name = self.underline_color_combo.currentText()
        self.page_label.set_overlay_color(self._get_overlay_qcolor(color_name))

    def _select_signature_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar imagen de firma",
            "",
            "Imágenes (*.png *.jpg *.jpeg *.bmp)",
        )
        if file_path:
            self.signature_image_path = file_path
            pixmap = QPixmap(file_path)
            if pixmap.isNull():
                self.signature_preview_pixmap = None
                self.signature_image_bytes = None
                QMessageBox.warning(self, "Imagen inválida", "No se pudo cargar la imagen de firma.")
                return
            self.signature_preview_pixmap = pixmap
            self.signature_image_bytes = None
            self.status_label.setText(
                f"Firma seleccionada: {os.path.basename(file_path)}. Haz clic en 'Colocar firma'."
            )

    def _open_signature_pad(self):
        dialog = SignaturePadDialog(self)
        if dialog.exec() != QDialog.Accepted or dialog.signature_pixmap is None:
            return

        self.signature_preview_pixmap = dialog.signature_pixmap
        self.signature_image_path = None
        self.signature_image_bytes = self._pixmap_to_png_bytes(dialog.signature_pixmap)
        self.status_label.setText("Firma capturada con touch. Haz clic en 'Colocar firma'.")
        self._sync_signature_preview_overlay()

    def _pixmap_to_png_bytes(self, pixmap):
        if pixmap is None or pixmap.isNull():
            return None
        buffer = QBuffer()
        buffer.open(QIODevice.WriteOnly)
        pixmap.save(buffer, "PNG")
        raw_bytes = bytes(buffer.data())
        buffer.close()
        return raw_bytes

    def _place_signature_preview(self):
        if not self.current_file or not self.doc:
            QMessageBox.warning(self, "Error", "Abre un PDF primero.")
            return
        if self.signature_preview_pixmap is None:
            QMessageBox.warning(self, "Error", "Selecciona una imagen o usa 'Firmar con touch' primero.")
            return

        page_number = self.signature_page_input.value() - 1
        if page_number < 0 or page_number >= self.total_pages:
            QMessageBox.warning(self, "Error", "Número de página fuera de rango.")
            return

        if page_number != self.current_page:
            self._jump_to_page(page_number)

        self.signature_preview_page = page_number
        self.signature_preview_pdf_rect = self._build_signature_pdf_rect(page_number)
        self._sync_signature_preview_overlay()
        self._focus_signature_preview()
        self.status_label.setText("Firma colocada. Arrástrala sobre la página y luego guarda.")

    def _focus_signature_preview(self):
        if not hasattr(self, "scroll_area"):
            return
        if self.signature_preview_pdf_rect is None or self.signature_preview_page != self.current_page:
            return

        view_rect = self._pdf_rect_to_view_rect(self.signature_preview_pdf_rect)
        if view_rect is None:
            return

        center = view_rect.center()
        self.scroll_area.ensureVisible(
            center.x(),
            center.y(),
            max(40, view_rect.width() // 2),
            max(30, view_rect.height() // 2),
        )

    def _fit_current_page_to_viewport(self):
        if not self.doc or self.total_pages <= 0 or not hasattr(self, "scroll_area"):
            return

        viewport = self.scroll_area.viewport()
        if viewport is None:
            return

        viewport_width = viewport.width()
        viewport_height = viewport.height()
        if viewport_width < 120 or viewport_height < 120:
            return

        page = self.doc[self.current_page]
        page_width = max(1.0, float(page.rect.width))
        page_height = max(1.0, float(page.rect.height))
        available_width = max(1.0, float(viewport_width - self._fit_padding))
        available_height = max(1.0, float(viewport_height - self._fit_padding))

        fit_zoom = (available_width / page_width) * self._fit_boost
        fit_zoom = max(0.35, min(4.0, fit_zoom))
        if abs(fit_zoom - self.zoom_factor) < 0.01:
            return

        self.zoom_factor = fit_zoom
        self._render_current_page()

    def _get_signature_default_size(self, page_number):
        page = self.doc[page_number]
        page_width = max(1.0, float(page.rect.width))
        page_height = max(1.0, float(page.rect.height))

        width = max(180.0, min(320.0, page_width * 0.32))
        aspect_ratio = 70.0 / 180.0
        if self.signature_preview_pixmap is not None and not self.signature_preview_pixmap.isNull():
            pix_width = max(1, self.signature_preview_pixmap.width())
            pix_height = max(1, self.signature_preview_pixmap.height())
            aspect_ratio = pix_height / pix_width

        height = width * aspect_ratio
        height = max(70.0, min(page_height * 0.2, height))
        return width, max(1.0, height)

    def _build_signature_pdf_rect(self, page_number, x=None, y=None, width=None, height=None):
        if not self.doc or page_number < 0 or page_number >= self.total_pages:
            return None

        page = self.doc[page_number]
        page_width = max(1.0, float(page.rect.width))
        page_height = max(1.0, float(page.rect.height))

        if width is None or height is None:
            width, height = self._get_signature_default_size(page_number)

        width = min(max(1.0, float(width)), page_width)
        height = min(max(1.0, float(height)), page_height)

        if x is None or y is None:
            margin_x = max(20.0, page_width * 0.04)
            margin_y = max(20.0, page_height * 0.04)
            x = page_width - width - margin_x
            y = page_height - height - margin_y

        clamped_x = min(max(float(x), 0.0), max(0.0, page_width - width))
        clamped_y = min(max(float(y), 0.0), max(0.0, page_height - height))
        return fitz.Rect(clamped_x, clamped_y, clamped_x + width, clamped_y + height)

    def _build_output_path(self, suffix):
        output_dir = get_output_dir("pdf")
        base_name = os.path.splitext(os.path.basename(self.current_file or "documento"))[0]
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(output_dir, f"{base_name}_{suffix}_{stamp}.pdf")

    def _selection_to_pdf_rect(self, view_rect):
        if not view_rect:
            return None

        pix = self.page_label.pixmap()
        if pix is None:
            return None

        view_w = max(1, pix.width())
        view_h = max(1, pix.height())
        page_w, page_h = self.current_page_size

        scale_x = page_w / view_w
        scale_y = page_h / view_h

        x0 = view_rect.left() * scale_x
        y0 = view_rect.top() * scale_y
        x1 = view_rect.right() * scale_x
        y1 = view_rect.bottom() * scale_y

        return fitz.Rect(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))

    def _pdf_rect_to_view_rect(self, pdf_rect):
        pix = self.page_label.pixmap()
        if pix is None:
            return None

        view_w = max(1, pix.width())
        view_h = max(1, pix.height())
        page_w, page_h = self.current_page_size

        scale_x = view_w / page_w
        scale_y = view_h / page_h

        x0 = int(pdf_rect.x0 * scale_x)
        y0 = int(pdf_rect.y0 * scale_y)
        x1 = int(pdf_rect.x1 * scale_x)
        y1 = int(pdf_rect.y1 * scale_y)
        return QRect(x0, y0, max(1, x1 - x0), max(1, y1 - y0)).normalized()

    def _sync_overlay_from_pending_rects(self):
        view_rects = []
        for rect, color_name in self.pending_pdf_rects:
            vr = self._pdf_rect_to_view_rect(rect)
            if vr is not None:
                view_rects.append((vr, self._get_overlay_qcolor(color_name)))
        self.page_label.set_saved_rects(view_rects)

    def _sync_signature_preview_overlay(self):
        if not hasattr(self, "page_label"):
            return

        if (
            self.signature_preview_pdf_rect is None
            or self.signature_preview_page is None
            or self.signature_preview_page != self.current_page
            or self.signature_preview_pixmap is None
        ):
            self.page_label.clear_signature_preview()
            return

        view_rect = self._pdf_rect_to_view_rect(self.signature_preview_pdf_rect)
        if view_rect is None:
            self.page_label.clear_signature_preview()
            return
        self.page_label.set_signature_preview(self.signature_preview_pixmap, view_rect)

    def _on_signature_preview_moved(self, view_rect):
        if view_rect is None or self.signature_preview_page != self.current_page:
            return

        pdf_rect = self._selection_to_pdf_rect(view_rect)
        if pdf_rect is None:
            return

        self.signature_preview_pdf_rect = self._build_signature_pdf_rect(
            self.current_page,
            pdf_rect.x0,
            pdf_rect.y0,
            pdf_rect.width,
            pdf_rect.height,
        )
        self.status_label.setText("Firma movida. Guarda cuando estés listo.")

    def _clear_pending_selections(self):
        if self.pending_pdf_rects:
            self._push_undo()
        self.pending_pdf_rects = []
        self.page_label.clear_saved_rects()
        self.status_label.setText("Selecciones limpiadas.")

    # ================= Undo / Redo =================

    def _bind_standard_shortcut(self, sequence, callback):
        shortcut = QShortcut(QKeySequence(sequence), self)
        shortcut.setContext(Qt.WidgetWithChildrenShortcut)
        shortcut.activated.connect(callback)
        self._standard_shortcuts.append(shortcut)

    def _invoke_on_focused_widget(self, method_name):
        focused = self.focusWidget()
        if focused is None:
            return False

        method = getattr(focused, method_name, None)
        if callable(method):
            method()
            return True

        return False

    def _copy_on_focused_widget(self):
        self._invoke_on_focused_widget("copy")

    def _paste_on_focused_widget(self):
        self._invoke_on_focused_widget("paste")

    def _cut_on_focused_widget(self):
        self._invoke_on_focused_widget("cut")

    def _select_all_on_focused_widget(self):
        self._invoke_on_focused_widget("selectAll")

    def _handle_undo_shortcut(self):
        if self._invoke_on_focused_widget("undo"):
            return
        self._undo_action()

    def _handle_redo_shortcut(self):
        if self._invoke_on_focused_widget("redo"):
            return
        self._redo_action()

    def _snapshot(self):
        """Captures the current editable state for undo/redo."""
        rects_copy = []
        if PDF_EDITOR_AVAILABLE:
            for r, c in self.pending_pdf_rects:
                rects_copy.append((fitz.Rect(r.x0, r.y0, r.x1, r.y1), c))
        sig_rect = None
        if PDF_EDITOR_AVAILABLE and self.signature_preview_pdf_rect is not None:
            sr = self.signature_preview_pdf_rect
            sig_rect = fitz.Rect(sr.x0, sr.y0, sr.x1, sr.y1)
        return {
            "file": self.current_file,
            "page": self.current_page,
            "rects": rects_copy,
            "sig_rect": sig_rect,
            "sig_page": self.signature_preview_page,
            "sig_pixmap": self.signature_preview_pixmap,
            "sig_bytes": self.signature_image_bytes,
            "sig_path": self.signature_image_path,
        }

    def _push_undo(self):
        """Saves current state to undo stack and clears redo stack."""
        self._undo_stack.append(self._snapshot())
        self._redo_stack.clear()
        self._update_undo_redo_buttons()

    def _update_undo_redo_buttons(self):
        has_doc = self.doc is not None
        if hasattr(self, "btn_undo"):
            self.btn_undo.setEnabled(has_doc and bool(self._undo_stack))
        if hasattr(self, "btn_redo"):
            self.btn_redo.setEnabled(has_doc and bool(self._redo_stack))

    def _undo_action(self):
        if not self._undo_stack:
            return
        self._redo_stack.append(self._snapshot())
        state = self._undo_stack.pop()
        self._restore_snapshot(state, is_undo=True)

    def _redo_action(self):
        if not self._redo_stack:
            return
        self._undo_stack.append(self._snapshot())
        state = self._redo_stack.pop()
        self._restore_snapshot(state, is_undo=False)

    def _restore_snapshot(self, state, is_undo=True):
        target_file = state.get("file")
        if target_file and target_file != self.current_file and os.path.isfile(target_file):
            if self.doc is not None:
                self.doc.close()
            self.doc = fitz.open(target_file)
            self.current_file = target_file
            self.total_pages = len(self.doc)
            self.page_count_label.setText(f"/ {self.total_pages}")
            self.underline_page_input.setMaximum(max(1, self.total_pages))
            self.signature_page_input.setMaximum(max(1, self.total_pages))
            self._set_controls_enabled(self.total_pages > 0)

        target_page = max(0, min(state.get("page", 0), max(0, self.total_pages - 1)))
        self.current_page = target_page
        self.page_input.setText(str(self.current_page + 1))

        self.pending_pdf_rects = state.get("rects", [])
        self.signature_preview_pdf_rect = state.get("sig_rect")
        self.signature_preview_page = state.get("sig_page")
        self.signature_preview_pixmap = state.get("sig_pixmap")
        self.signature_image_bytes = state.get("sig_bytes")
        self.signature_image_path = state.get("sig_path")

        self._render_current_page()
        msg = "Acción revertida." if is_undo else "Acción reestablecida."
        self.status_label.setText(msg)
        self._update_undo_redo_buttons()

    def _get_underline_color(self, color_name=None):
        color_name = color_name or self.underline_color_combo.currentText()
        colors = {
            "Amarillo": (1.0, 0.85, 0.0),
            "Verde": (0.0, 0.7, 0.2),
            "Rosa": (0.9, 0.2, 0.6),
            "Azul": (0.1, 0.4, 0.9),
        }
        return colors.get(color_name, (1.0, 0.85, 0.0))

    def _get_overlay_qcolor(self, color_name):
        colors = {
            "Amarillo": QColor(255, 220, 60, 95),
            "Verde": QColor(74, 222, 128, 95),
            "Rosa": QColor(244, 114, 182, 95),
            "Azul": QColor(96, 165, 250, 95),
        }
        return colors.get(color_name, QColor(255, 220, 60, 95))

    def _underline_selection(self):
        if not self.current_file or not self.doc:
            QMessageBox.warning(self, "Error", "Abre un PDF primero.")
            return
        if not self.pending_pdf_rects:
            QMessageBox.warning(self, "Error", "Haz una o varias selecciones arrastrando sobre la página.")
            return

        page_number = self.underline_page_input.value() - 1
        if page_number != self.current_page:
            QMessageBox.warning(self, "Página distinta", "La selección es de la página actual. Cambia a esa página o vuelve a seleccionar.")
            return

        out_path = self._build_output_path("subrayado")
        try:
            doc = fitz.open(self.current_file)
            page = doc[page_number]

            words = page.get_text("words")
            matched = 0
            seen_words = set()
            for selection_pdf_rect, color_name in self.pending_pdf_rects:
                stroke_color = self._get_underline_color(color_name)
                for word in words:
                    wrect = fitz.Rect(word[0], word[1], word[2], word[3])
                    if not wrect.intersects(selection_pdf_rect):
                        continue
                    key = (round(wrect.x0, 2), round(wrect.y0, 2), round(wrect.x1, 2), round(wrect.y1, 2))
                    if key in seen_words:
                        continue
                    seen_words.add(key)
                    annot = page.add_underline_annot(wrect)
                    if annot:
                        annot.set_colors(stroke=stroke_color)
                        annot.update()
                        matched += 1

            if matched == 0:
                doc.close()
                QMessageBox.information(self, "Sin texto", "No se detectó texto en el área seleccionada.")
                return

            doc.save(out_path)
            doc.close()
            self._push_undo()
            self._load_pdf_file(out_path)
            self.status_label.setText("Subrayados aplicados correctamente.")
            QMessageBox.information(self, "Éxito", f"Subrayados aplicados y PDF guardado en:\n{out_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo subrayar la selección: {e}")

    def _insert_signature(self):
        if not self.current_file:
            QMessageBox.warning(self, "Error", "Abre un PDF primero.")
            return
        if not self.signature_image_path and not self.signature_image_bytes:
            QMessageBox.warning(self, "Error", "Selecciona una imagen o crea una firma con touch primero.")
            return

        if self.signature_preview_pdf_rect is not None and self.signature_preview_page is not None:
            page_number = self.signature_preview_page
            rect = self.signature_preview_pdf_rect
        else:
            page_number = self.signature_page_input.value() - 1
            rect = self._build_signature_pdf_rect(page_number)

        out_path = self._build_output_path("firmado")

        try:
            doc = fitz.open(self.current_file)
            if page_number < 0 or page_number >= len(doc):
                doc.close()
                QMessageBox.warning(self, "Error", "Número de página fuera de rango.")
                return

            page = doc[page_number]
            if self.signature_image_bytes:
                page.insert_image(rect, stream=self.signature_image_bytes, keep_proportion=True)
            elif self.signature_image_path:
                page.insert_image(rect, filename=self.signature_image_path, keep_proportion=True)
            else:
                doc.close()
                QMessageBox.warning(self, "Error", "No hay firma disponible para insertar.")
                return

            doc.save(out_path)
            doc.close()
            self._push_undo()
            self.signature_preview_pdf_rect = None
            self.signature_preview_page = None
            if hasattr(self, "page_label"):
                self.page_label.clear_signature_preview()
            self._load_pdf_file(out_path)
            QMessageBox.information(self, "Éxito", f"Firma insertada y PDF guardado en:\n{out_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo insertar la firma: {e}")
