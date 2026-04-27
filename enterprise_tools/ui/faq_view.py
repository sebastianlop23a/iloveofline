"""
faq_view.py — Vista de preguntas frecuentes y guías paso a paso
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QMessageBox
import webbrowser
import os


# Lista de archivos FAQ HTML
FAQ_FILES = [
    ("¿Problemas de audio y video?", "faqs/faq1.html"),
    ("¿problemas con la vpn open?", "faqs/faq2.html"),
    ("¿problemas con la vpn shophos?", "faqs/faq3.html"),
    ("¿computador lento?", "faqs/faq4.html"),
    ("¡problemas con microsoft teams?", "faqs/faq5.html"),
    ("¡problemas con el glpi?", "faqs/faq6.html"),
]


class FAQView(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        self.label = QLabel("Preguntas frecuentes y guías")
        self.list_widget = QListWidget()

        # Cargar preguntas en la lista
        for question, _ in FAQ_FILES:
            self.list_widget.addItem(question)

        # Evento al hacer clic
        self.list_widget.itemClicked.connect(self._open_in_browser)

        layout.addWidget(self.label)
        layout.addWidget(self.list_widget)
        self.setLayout(layout)

        # Seleccionar primer elemento por defecto
        if FAQ_FILES:
            self.list_widget.setCurrentRow(0)

    def _open_in_browser(self, item):
        """
        Abre el archivo HTML correspondiente en el navegador.
        """

        index = self.list_widget.row(item)

        if not (0 <= index < len(FAQ_FILES)):
            return

        _, rel_path = FAQ_FILES[index]

        # Obtener ruta base del proyecto
        base_dir = os.path.dirname(os.path.abspath(__file__))

        # Construir ruta absoluta
        html_path = os.path.normpath(os.path.join(base_dir, "..", rel_path))

        # Verificar existencia del archivo
        if not os.path.exists(html_path):
            QMessageBox.warning(
                self,
                "Archivo no encontrado",
                f"No se encontró la guía:\n{html_path}"
            )
            return

        # Convertir ruta a formato URL compatible
        file_url = f"file:///{html_path.replace(os.sep, '/')}"

        # Abrir en navegador
        webbrowser.open(file_url)
