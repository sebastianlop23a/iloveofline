import os
import sys
from io import BytesIO

from PySide6.QtGui import QPixmap

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except Exception:
    fitz = None
    PYMUPDF_AVAILABLE = False


def _resolve_poppler_path():
    env_poppler = os.environ.get("POPPLER_PATH")
    if env_poppler and os.path.isdir(env_poppler):
        return env_poppler

    project_root = os.path.dirname(os.path.dirname(__file__))
    executable_root = os.path.dirname(sys.executable)

    candidates = [
        os.path.join(project_root, "poppler", "bin"),
        os.path.join(project_root, "poppler", "Library", "bin"),
        os.path.join(executable_root, "poppler", "bin"),
        os.path.join(executable_root, "poppler", "Library", "bin"),
    ]

    for candidate in candidates:
        if os.path.isdir(candidate):
            return candidate
    return None


def _pil_image_to_qpixmap(pil_image):
    buffer = BytesIO()
    pil_image.save(buffer, format="PNG")
    pixmap = QPixmap()
    if pixmap.loadFromData(buffer.getvalue(), "PNG"):
        return pixmap
    return None


def _first_page_with_pymupdf(pdf_path, max_width, max_height):
    if not PYMUPDF_AVAILABLE:
        return None

    document = None
    try:
        document = fitz.open(pdf_path)
        if document.page_count == 0:
            return None

        page = document.load_page(0)
        rect = page.rect
        if rect.width <= 0 or rect.height <= 0:
            zoom = 1.0
        else:
            zoom = min(max_width / rect.width, max_height / rect.height)
            zoom = max(zoom, 0.1)

        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        pixmap = QPixmap()
        if pixmap.loadFromData(pix.tobytes("png"), "PNG"):
            return pixmap
        return None
    except Exception:
        return None
    finally:
        if document is not None:
            document.close()


def _first_page_with_pdf2image(pdf_path, max_width, max_height):
    try:
        from pdf2image import convert_from_path

        poppler_path = _resolve_poppler_path()
        images = convert_from_path(
            pdf_path,
            first_page=1,
            last_page=1,
            size=(max_width, max_height),
            poppler_path=poppler_path,
        )
        if not images:
            return None
        return _pil_image_to_qpixmap(images[0])
    except Exception:
        return None


def get_first_page_pixmap(pdf_path, max_width=160, max_height=220):
    if not pdf_path or not os.path.isfile(pdf_path):
        return None

    pixmap = _first_page_with_pymupdf(pdf_path, max_width, max_height)
    if pixmap is not None:
        return pixmap

    return _first_page_with_pdf2image(pdf_path, max_width, max_height)
