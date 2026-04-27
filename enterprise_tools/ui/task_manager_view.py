"""
task_manager_view.py - Administrador inteligente de tareas
"""

import os
from datetime import datetime

from PySide6.QtCore import Qt, QTimer, QObject, QThread, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QProgressBar,
    QTextEdit,
    QMessageBox,
)

from services.task_manager_service import TaskManagerService


class _TaskManagerJobWorker(QObject):
    finished = Signal(str, object)
    failed = Signal(str, str)

    def __init__(self, operation):
        super().__init__()
        self.operation = operation

    def run(self):
        try:
            if self.operation == "refresh":
                snapshot = TaskManagerService.get_system_snapshot()
                processes = TaskManagerService.get_top_processes(limit=30)
                recommendations = TaskManagerService.build_recommendations(snapshot, processes)
                payload = {
                    "snapshot": snapshot,
                    "processes": processes,
                    "recommendations": recommendations,
                }
                self.finished.emit(self.operation, payload)
                return

            if self.operation == "close_heavy":
                action_result = TaskManagerService.terminate_heavy_processes(limit=5, min_memory_mb=900.0)
                snapshot = TaskManagerService.get_system_snapshot()
                processes = TaskManagerService.get_top_processes(limit=30)
                recommendations = TaskManagerService.build_recommendations(snapshot, processes)
                payload = {
                    "action_result": action_result,
                    "snapshot": snapshot,
                    "processes": processes,
                    "recommendations": recommendations,
                }
                self.finished.emit(self.operation, payload)
                return

            if self.operation == "close_common":
                action_result = TaskManagerService.terminate_common_user_apps(limit=12)
                snapshot = TaskManagerService.get_system_snapshot()
                processes = TaskManagerService.get_top_processes(limit=30)
                recommendations = TaskManagerService.build_recommendations(snapshot, processes)
                payload = {
                    "action_result": action_result,
                    "snapshot": snapshot,
                    "processes": processes,
                    "recommendations": recommendations,
                }
                self.finished.emit(self.operation, payload)
                return

            if self.operation == "optimize":
                optimize_result = TaskManagerService.optimize_system()
                snapshot = TaskManagerService.get_system_snapshot()
                processes = TaskManagerService.get_top_processes(limit=30)
                recommendations = TaskManagerService.build_recommendations(snapshot, processes)
                payload = {
                    "optimize_result": optimize_result,
                    "snapshot": snapshot,
                    "processes": processes,
                    "recommendations": recommendations,
                }
                self.finished.emit(self.operation, payload)
                return

            self.failed.emit(self.operation, f"Operación desconocida: {self.operation}")
        except Exception as exc:
            self.failed.emit(self.operation, str(exc))


class TaskManagerView(QWidget):
    def __init__(self):
        super().__init__()
        self.snapshot = {}
        self.processes = []
        self._active_thread = None
        self._active_worker = None
        self._busy_operation = None
        self._refresh_interval_ms = 15000
        self._init_ui()
        self._apply_view_styles()

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(self._refresh_interval_ms)

        self.refresh_data()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        title = QLabel("Administrador inteligente de tareas")
        title.setObjectName("Title")

        subtitle = QLabel(
            "Monitorea rendimiento, recibe consejos automáticos y aplica optimización segura del equipo"
        )
        subtitle.setObjectName("Subtitle")
        subtitle.setWordWrap(True)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)

        self.btn_refresh = QPushButton("Actualizar")
        self.btn_refresh.setObjectName("PrimaryButton")
        self.btn_refresh.clicked.connect(self.refresh_data)

        self.btn_optimize = QPushButton("Optimizar equipo")
        self.btn_optimize.setObjectName("PrimaryButton")
        self.btn_optimize.clicked.connect(self.optimize_system)

        self.btn_open_native = QPushButton("Abrir Administrador de tareas")
        self.btn_open_native.setObjectName("PrimaryButton")
        self.btn_open_native.clicked.connect(self.open_native_task_manager)

        action_row.addWidget(self.btn_refresh)
        action_row.addWidget(self.btn_optimize)
        action_row.addWidget(self.btn_open_native)
        action_row.addStretch()

        metrics_card = QFrame()
        metrics_card.setObjectName("MainCard")
        metrics_layout = QHBoxLayout()
        metrics_layout.setContentsMargins(12, 12, 12, 12)
        metrics_layout.setSpacing(12)

        self.cpu_card, self.cpu_bar, self.cpu_label = self._build_metric_widget("CPU")
        self.ram_card, self.ram_bar, self.ram_label = self._build_metric_widget("RAM")
        self.disk_card, self.disk_bar, self.disk_label = self._build_metric_widget("Disco")

        metrics_layout.addWidget(self.cpu_card)
        metrics_layout.addWidget(self.ram_card)
        metrics_layout.addWidget(self.disk_card)
        metrics_card.setLayout(metrics_layout)

        body_row = QHBoxLayout()
        body_row.setSpacing(10)

        actions_card = QFrame()
        actions_card.setObjectName("MainCard")
        actions_layout = QVBoxLayout()
        actions_layout.setContentsMargins(12, 12, 12, 12)
        actions_layout.setSpacing(8)

        actions_title = QLabel("Acciones rápidas")
        actions_title.setObjectName("TaskSectionTitle")

        actions_desc = QLabel(
            "Cierra apps pesadas o ventanas comunes cuando el equipo esté saturado. "
            "Estas acciones solo afectan procesos de usuario no críticos."
        )
        actions_desc.setWordWrap(True)
        actions_desc.setObjectName("TaskResult")

        self.btn_close_heavy = QPushButton("Cerrar apps pesadas automáticamente")
        self.btn_close_heavy.setObjectName("PrimaryButton")
        self.btn_close_heavy.clicked.connect(self.close_heavy_windows)

        self.btn_close_common = QPushButton("Cerrar ventanas comunes (navegadores/chat)")
        self.btn_close_common.setObjectName("PrimaryButton")
        self.btn_close_common.clicked.connect(self.close_common_windows)

        self.process_hint_label = QLabel("Procesos intensivos detectados: --")
        self.process_hint_label.setObjectName("TaskResult")
        self.process_hint_label.setWordWrap(True)

        self.actions_log = QTextEdit()
        self.actions_log.setReadOnly(True)
        self.actions_log.setPlaceholderText("Aquí verás el detalle de acciones aplicadas.")

        actions_layout.addWidget(actions_title)
        actions_layout.addWidget(actions_desc)
        actions_layout.addWidget(self.btn_close_heavy)
        actions_layout.addWidget(self.btn_close_common)
        actions_layout.addWidget(self.process_hint_label)
        actions_layout.addWidget(self.actions_log, 1)
        actions_card.setLayout(actions_layout)

        advice_card = QFrame()
        advice_card.setObjectName("MainCard")
        advice_layout = QVBoxLayout()
        advice_layout.setContentsMargins(12, 12, 12, 12)
        advice_layout.setSpacing(8)

        advice_title = QLabel("Consejos inteligentes")
        advice_title.setObjectName("TaskSectionTitle")

        self.advice_text = QTextEdit()
        self.advice_text.setReadOnly(True)
        self.advice_text.setPlaceholderText("Aquí verás recomendaciones según el estado del equipo.")

        self.result_label = QLabel("Estado: listo")
        self.result_label.setObjectName("TaskResult")
        self.result_label.setWordWrap(True)

        advice_layout.addWidget(advice_title)
        advice_layout.addWidget(self.advice_text, 1)
        advice_layout.addWidget(self.result_label)
        advice_card.setLayout(advice_layout)

        body_row.addWidget(actions_card, 1)
        body_row.addWidget(advice_card, 1)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(action_row)
        layout.addWidget(metrics_card)
        layout.addLayout(body_row, 1)

        self.setLayout(layout)

    def _build_metric_widget(self, title):
        card = QFrame()
        card.setObjectName("TaskMetricCard")

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setObjectName("TaskMetricTitle")

        progress = QProgressBar()
        progress.setRange(0, 100)
        progress.setValue(0)
        progress.setTextVisible(True)

        value_label = QLabel("--")
        value_label.setObjectName("TaskMetricValue")

        layout.addWidget(title_label)
        layout.addWidget(progress)
        layout.addWidget(value_label)

        card.setLayout(layout)
        return card, progress, value_label

    def _apply_view_styles(self):
        self.setStyleSheet(
            """
QLabel {
    color: #111827;
}
#Title {
    color: #111827;
}
#Subtitle {
    color: #475569;
}
#TaskMetricCard {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
}
#TaskMetricTitle {
    color: #475569;
    font-size: 12px;
    font-weight: 700;
}
#TaskMetricValue {
    color: #111827;
    font-size: 13px;
    font-weight: 700;
}
#TaskSectionTitle {
    color: #111827;
    font-size: 15px;
    font-weight: 700;
}
#TaskResult {
    color: #475569;
    font-size: 12px;
}
QProgressBar {
    background-color: #F1F5F9;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    color: #111827;
    text-align: center;
    min-height: 18px;
}
QProgressBar::chunk {
    background-color: #A70064;
    border-radius: 7px;
}
QTableWidget {
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    background-color: #FFFFFF;
    alternate-background-color: #F8FAFC;
    color: #111827;
    gridline-color: #E5E7EB;
    selection-background-color: #EEF2FF;
    selection-color: #111827;
}
QTableWidget::item {
    color: #111827;
}
QHeaderView::section {
    background-color: #F8FAFC;
    color: #334155;
    border: none;
    border-bottom: 1px solid #E2E8F0;
    padding: 6px;
    font-weight: 700;
}
QTextEdit {
    background-color: #FFFFFF;
    color: #111827;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 8px;
}
QPushButton#PrimaryButton {
    background-color: #A70064;
    color: #FFFFFF;
    border: none;
    border-radius: 10px;
    padding: 8px 12px;
    font-weight: 700;
}
QPushButton#PrimaryButton:hover {
    background-color: #87004F;
}
            """
        )

    def refresh_data(self):
        self._start_background_job("refresh")

    def _start_background_job(self, operation):
        if self._busy_operation is not None:
            return

        self._set_busy_state(True, operation)

        self._active_thread = QThread(self)
        self._active_worker = _TaskManagerJobWorker(operation)
        self._active_worker.moveToThread(self._active_thread)

        self._active_thread.started.connect(self._active_worker.run)
        self._active_worker.finished.connect(self._on_background_job_finished)
        self._active_worker.failed.connect(self._on_background_job_failed)

        self._active_worker.finished.connect(self._active_thread.quit)
        self._active_worker.failed.connect(self._active_thread.quit)

        self._active_thread.finished.connect(self._active_worker.deleteLater)
        self._active_thread.finished.connect(self._active_thread.deleteLater)
        self._active_thread.finished.connect(self._on_background_thread_finished)

        self._active_thread.start()

    def _set_busy_state(self, busy, operation=None):
        if busy:
            self._busy_operation = operation
            self.btn_refresh.setEnabled(False)
            self.btn_optimize.setEnabled(False)
            self.btn_close_heavy.setEnabled(False)
            self.btn_close_common.setEnabled(False)

            if hasattr(self, "refresh_timer") and self.refresh_timer.isActive():
                self.refresh_timer.stop()

            status_by_operation = {
                "refresh": "Estado: actualizando diagnóstico del equipo...",
                "optimize": "Estado: optimizando el equipo, por favor espera...",
                "close_heavy": "Estado: cerrando apps pesadas...",
                "close_common": "Estado: cerrando apps comunes...",
            }
            self.result_label.setText(status_by_operation.get(operation, "Estado: ejecutando acción..."))
            return

        self._busy_operation = None
        self.btn_refresh.setEnabled(True)
        self.btn_optimize.setEnabled(True)
        psutil_available = TaskManagerService.is_available()
        self.btn_close_heavy.setEnabled(psutil_available)
        self.btn_close_common.setEnabled(psutil_available)

        if hasattr(self, "refresh_timer") and not self.refresh_timer.isActive():
            self.refresh_timer.start(self._refresh_interval_ms)

    def _on_background_job_finished(self, operation, payload):
        snapshot = payload.get("snapshot") or {}
        processes = payload.get("processes") or []
        recommendations = payload.get("recommendations") or []

        self.snapshot = snapshot
        self.processes = processes
        self._update_metrics()
        self._update_process_hint()
        self._show_recommendations(recommendations)

        if operation in {"close_heavy", "close_common"}:
            action_result = payload.get("action_result") or {}
            summary = action_result.get("summary", "Acción completada")
            self.result_label.setText(summary)
            action_name = (
                "Cierre de apps pesadas"
                if operation == "close_heavy"
                else "Cierre de apps comunes"
            )
            self._append_action_log(action_name, action_result)
            return

        if operation == "optimize":
            result = payload.get("optimize_result") or {}
            details = result.get("details") or []
            details_text = "\n".join(details) if details else "Sin acciones adicionales."
            summary = result.get("summary", "Optimización finalizada")
            self.result_label.setText(summary)
            self._append_action_log("Optimización de equipo", result)

            QMessageBox.information(
                self,
                "Optimización completada",
                f"{summary}\n\nDetalle:\n{details_text}",
            )
            return

        if not TaskManagerService.is_available():
            self.result_label.setText("Estado: diagnóstico básico activo (instala psutil para métricas avanzadas).")
        else:
            self.result_label.setText("Estado: diagnóstico actualizado correctamente.")

    def _on_background_job_failed(self, operation, message):
        operation_name = {
            "refresh": "actualización",
            "optimize": "optimización",
            "close_heavy": "cierre de apps pesadas",
            "close_common": "cierre de apps comunes",
        }.get(operation, "operación")
        self.result_label.setText(f"Estado: error durante {operation_name}.")
        QMessageBox.warning(
            self,
            "Operación fallida",
            f"No se pudo completar la {operation_name}:\n{message}",
        )

    def _on_background_thread_finished(self):
        self._active_worker = None
        self._active_thread = None
        self._set_busy_state(False)

    def _update_metrics(self):
        cpu = self.snapshot.get("cpu_percent")
        ram = self.snapshot.get("ram_percent")
        disk = self.snapshot.get("disk_percent")

        self.cpu_bar.setValue(int(cpu if cpu is not None else 0))
        self.ram_bar.setValue(int(ram if ram is not None else 0))
        self.disk_bar.setValue(int(disk if disk is not None else 0))

        if cpu is None:
            self.cpu_label.setText("No disponible")
        else:
            self.cpu_label.setText(f"Uso actual: {cpu:.1f}%")

        if ram is None:
            self.ram_label.setText("No disponible")
        else:
            used = self.snapshot.get("ram_used_gb")
            total = self.snapshot.get("ram_total_gb")
            if used is not None and total is not None:
                self.ram_label.setText(f"{used:.1f} / {total:.1f} GB ({ram:.1f}%)")
            else:
                self.ram_label.setText(f"Uso RAM: {ram:.1f}%")

        if disk is None:
            self.disk_label.setText("No disponible")
        else:
            free = self.snapshot.get("disk_free_gb")
            total = self.snapshot.get("disk_total_gb")
            if free is not None and total is not None:
                self.disk_label.setText(f"Libre: {free:.1f} / {total:.1f} GB ({disk:.1f}% usado)")
            else:
                self.disk_label.setText(f"Uso disco: {disk:.1f}%")

    def _update_process_hint(self):
        if not self.processes:
            self.process_hint_label.setText("Procesos intensivos detectados: sin datos")
            return

        heavy_processes = [
            process_info
            for process_info in self.processes
            if float(process_info.get("memory_mb", 0.0)) >= 700.0
        ]

        if not heavy_processes:
            self.process_hint_label.setText("Procesos intensivos detectados: ninguno relevante por ahora")
            return

        preview = ", ".join(
            f"{process_info.get('name', 'Proceso')} ({float(process_info.get('memory_mb', 0.0)):.0f} MB)"
            for process_info in heavy_processes[:4]
        )
        self.process_hint_label.setText(f"Procesos intensivos detectados: {preview}")

    def _append_action_log(self, action_name, result):
        summary = result.get("summary", "Acción completada")
        details = result.get("details") or []

        lines = [f"[{datetime.now().strftime('%H:%M:%S')}] {action_name}: {summary}"]
        for detail in details[:8]:
            lines.append(f"• {detail}")
        if len(details) > 8:
            lines.append(f"• ... {len(details) - 8} detalles adicionales")

        entry = "\n".join(lines)
        existing = self.actions_log.toPlainText().strip()
        if existing:
            self.actions_log.setPlainText(f"{existing}\n\n{entry}")
        else:
            self.actions_log.setPlainText(entry)

        scrollbar = self.actions_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _show_recommendations(self, recommendations):
        lines = []
        for recommendation in recommendations:
            lines.append(f"• {recommendation}")
        self.advice_text.setPlainText("\n".join(lines))

    def optimize_system(self):
        self._start_background_job("optimize")

    def close_heavy_windows(self):
        confirm = QMessageBox.question(
            self,
            "Confirmar cierre de apps pesadas",
            "Se intentarán cerrar procesos de usuario con alto consumo de RAM. ¿Deseas continuar?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        self._start_background_job("close_heavy")

    def close_common_windows(self):
        confirm = QMessageBox.question(
            self,
            "Confirmar cierre de apps comunes",
            "Esta acción puede cerrar navegadores, chat y otras apps de uso común. ¿Continuar?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        self._start_background_job("close_common")

    def open_native_task_manager(self):
        try:
            if hasattr(os, "startfile"):
                os.startfile("taskmgr.exe")
            else:
                QMessageBox.information(self, "No disponible", "Esta acción está disponible en Windows.")
        except Exception as exc:
            QMessageBox.warning(self, "No disponible", f"No se pudo abrir el Administrador de tareas: {exc}")
