"""
conversion_service.py - Conversiones amplias para el módulo PDF
"""

from __future__ import annotations

import html
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from dataclasses import dataclass

from PyPDF2 import PdfReader

from services.pdf_service import (
    PYMUPDF_AVAILABLE,
    fitz,
    images_to_pdf,
    pdf_to_images,
)


@dataclass(frozen=True)
class ConversionOperation:
    key: str
    label: str
    source_extensions: tuple[str, ...]
    output_kind: str  # file | folder
    output_extension: str
    source_filter: str


IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff")


CONVERSION_OPERATIONS: tuple[ConversionOperation, ...] = (
    ConversionOperation(
        key="pdf_to_docx",
        label="PDF → DOCX",
        source_extensions=(".pdf",),
        output_kind="file",
        output_extension=".docx",
        source_filter="PDF (*.pdf)",
    ),
    ConversionOperation(
        key="pdf_to_txt",
        label="PDF → TXT",
        source_extensions=(".pdf",),
        output_kind="file",
        output_extension=".txt",
        source_filter="PDF (*.pdf)",
    ),
    ConversionOperation(
        key="pdf_to_html",
        label="PDF → HTML",
        source_extensions=(".pdf",),
        output_kind="file",
        output_extension=".html",
        source_filter="PDF (*.pdf)",
    ),
    ConversionOperation(
        key="pdf_to_png",
        label="PDF → PNG (todas las páginas)",
        source_extensions=(".pdf",),
        output_kind="folder",
        output_extension="",
        source_filter="PDF (*.pdf)",
    ),
    ConversionOperation(
        key="pdf_to_jpg",
        label="PDF → JPG (todas las páginas)",
        source_extensions=(".pdf",),
        output_kind="folder",
        output_extension="",
        source_filter="PDF (*.pdf)",
    ),
    ConversionOperation(
        key="image_to_pdf",
        label="Imagen → PDF",
        source_extensions=IMAGE_EXTENSIONS,
        output_kind="file",
        output_extension=".pdf",
        source_filter="Imágenes (*.png *.jpg *.jpeg *.bmp *.webp *.tif *.tiff)",
    ),
    ConversionOperation(
        key="txt_to_pdf",
        label="TXT → PDF",
        source_extensions=(".txt",),
        output_kind="file",
        output_extension=".pdf",
        source_filter="Texto (*.txt)",
    ),
    ConversionOperation(
        key="html_to_pdf",
        label="HTML → PDF",
        source_extensions=(".html", ".htm"),
        output_kind="file",
        output_extension=".pdf",
        source_filter="HTML (*.html *.htm)",
    ),
)


_OPERATIONS_BY_KEY = {item.key: item for item in CONVERSION_OPERATIONS}


def get_conversion_operations() -> list[dict]:
    return [
        {
            "key": operation.key,
            "label": operation.label,
            "source_extensions": list(operation.source_extensions),
            "output_kind": operation.output_kind,
            "output_extension": operation.output_extension,
            "source_filter": operation.source_filter,
        }
        for operation in CONVERSION_OPERATIONS
    ]


def execute_conversion(operation_key: str, input_source, output_target: str) -> str:
    if operation_key not in _OPERATIONS_BY_KEY:
        raise ValueError(f"Operación no soportada: {operation_key}")

    operation = _OPERATIONS_BY_KEY[operation_key]

    if operation_key == "image_to_pdf":
        if isinstance(input_source, str):
            input_paths = [input_source]
        elif isinstance(input_source, (list, tuple)):
            input_paths = [path for path in input_source if isinstance(path, str)]
        else:
            input_paths = []

        if not input_paths:
            raise ValueError("Debes seleccionar al menos una imagen para convertir a PDF.")

        for path in input_paths:
            source_ext = os.path.splitext(path)[1].lower()
            if source_ext not in operation.source_extensions:
                supported = ", ".join(operation.source_extensions)
                raise ValueError(
                    f"Formato de imagen no válido. Permitidos: {supported}"
                )

        os.makedirs(os.path.dirname(output_target), exist_ok=True)
        images_to_pdf(input_paths, output_target)
        return output_target

    if not isinstance(input_source, str):
        raise ValueError(f"La operación {operation.label} requiere un único archivo origen.")

    input_path = input_source
    source_ext = os.path.splitext(input_path)[1].lower()

    if source_ext not in operation.source_extensions:
        supported = ", ".join(operation.source_extensions)
        raise ValueError(
            f"Formato de origen no válido para {operation.label}. Permitidos: {supported}"
        )

    os.makedirs(os.path.dirname(output_target), exist_ok=True)

    if operation_key == "pdf_to_docx":
        _convert_pdf_to_docx(input_path, output_target)
        return output_target

    if operation_key == "pdf_to_txt":
        _convert_pdf_to_txt(input_path, output_target)
        return output_target

    if operation_key == "pdf_to_html":
        _convert_pdf_to_html(input_path, output_target)
        return output_target

    if operation_key == "pdf_to_png":
        os.makedirs(output_target, exist_ok=True)
        pdf_to_images(input_path, output_target, image_format="png")
        return output_target

    if operation_key == "pdf_to_jpg":
        os.makedirs(output_target, exist_ok=True)
        pdf_to_images(input_path, output_target, image_format="jpg")
        return output_target

    if operation_key == "txt_to_pdf":
        _convert_text_file_to_pdf(input_path, output_target)
        return output_target

    if operation_key == "html_to_pdf":
        _convert_html_file_to_pdf(input_path, output_target)
        return output_target

    raise ValueError(f"Operación no implementada: {operation_key}")


def _convert_pdf_to_docx(pdf_path: str, output_docx_path: str):
    try:
        from pdf2docx import Converter
    except Exception as exc:
        raise RuntimeError(
            "Para convertir PDF a DOCX instala la dependencia 'pdf2docx'."
        ) from exc

    converter = Converter(pdf_path)
    try:
        converter.convert(output_docx_path, start=0, end=None)
    finally:
        converter.close()


def _convert_pdf_to_txt(pdf_path: str, output_txt_path: str):
    if PYMUPDF_AVAILABLE:
        document = fitz.open(pdf_path)
        text_blocks: list[str] = []
        for page in document:
            text_blocks.append(page.get_text("text"))
        document.close()
    else:
        reader = PdfReader(pdf_path)
        text_blocks = [(page.extract_text() or "") for page in reader.pages]

    full_text = "\n\n".join(text_blocks)
    with open(output_txt_path, "w", encoding="utf-8") as file:
        file.write(full_text)


def _convert_pdf_to_html(pdf_path: str, output_html_path: str):
    page_html_blocks: list[str] = []

    if PYMUPDF_AVAILABLE:
        document = fitz.open(pdf_path)
        try:
            for index, page in enumerate(document, start=1):
                page_html = page.get_text("html")
                page_html_blocks.append(
                    f"<section><h2>Página {index}</h2>{page_html}</section>"
                )
        finally:
            document.close()
    else:
        reader = PdfReader(pdf_path)
        for index, page in enumerate(reader.pages, start=1):
            text = html.escape(page.extract_text() or "")
            page_html_blocks.append(f"<section><h2>Página {index}</h2><pre>{text}</pre></section>")

    html_doc = """<!DOCTYPE html>
<html lang=\"es\">
<head>
    <meta charset=\"utf-8\" />
    <title>Conversión PDF a HTML</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 24px; line-height: 1.45; }
        section { margin-bottom: 28px; }
        h2 { font-size: 18px; margin-bottom: 10px; color: #333333; }
        pre { white-space: pre-wrap; word-break: break-word; }
    </style>
</head>
<body>
{content}
</body>
</html>
""".format(content="\n".join(page_html_blocks))

    with open(output_html_path, "w", encoding="utf-8") as file:
        file.write(html_doc)


def _convert_text_file_to_pdf(text_path: str, output_pdf_path: str):
    with open(text_path, "r", encoding="utf-8", errors="ignore") as file:
        content = file.read()
    _write_plain_text_to_pdf(content, output_pdf_path)


def _convert_html_file_to_pdf(html_path: str, output_pdf_path: str):
    with open(html_path, "r", encoding="utf-8", errors="ignore") as file:
        raw_html = file.read()
    plain_text = _strip_html_tags(raw_html)
    _write_plain_text_to_pdf(plain_text, output_pdf_path)


def _strip_html_tags(raw_html: str) -> str:
    cleaned = re.sub(r"<script[\s\S]*?</script>", "", raw_html, flags=re.IGNORECASE)
    cleaned = re.sub(r"<style[\s\S]*?</style>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = html.unescape(cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _write_plain_text_to_pdf(content: str, output_pdf_path: str):
    if not PYMUPDF_AVAILABLE:
        raise RuntimeError("Para convertir TXT/HTML a PDF se requiere PyMuPDF.")

    document = fitz.open()
    page_width, page_height = fitz.paper_size("a4")
    margin = 42
    lines = []

    for paragraph in content.splitlines() or [""]:
        wrapped = paragraph
        while len(wrapped) > 105:
            lines.append(wrapped[:105])
            wrapped = wrapped[105:]
        lines.append(wrapped)

    if not lines:
        lines = [""]

    y_start = margin
    line_height = 14
    max_lines_per_page = max(1, int((page_height - (margin * 2)) / line_height))

    for chunk_start in range(0, len(lines), max_lines_per_page):
        page = document.new_page(width=page_width, height=page_height)
        chunk = lines[chunk_start: chunk_start + max_lines_per_page]
        y = y_start
        for line in chunk:
            page.insert_text((margin, y), line, fontsize=10)
            y += line_height

    document.save(output_pdf_path)
    document.close()


