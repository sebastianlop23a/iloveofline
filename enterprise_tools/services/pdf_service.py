"""
pdf_service.py - PDF manipulation service
"""

import os
import sys
import tempfile
import shutil

from PIL import Image
from PyPDF2 import PdfMerger, PdfReader, PdfWriter

from utils.logger import logging

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


def decrypt_pdf(pdf_path, _password, output_path):
    reader = PdfReader(pdf_path)
    tried_passwords = ["", "owner", "user", "1234", "12345", "password", "admin"]
    success = False

    if reader.is_encrypted:
        for pwd in tried_passwords:
            try:
                if reader.decrypt(pwd):
                    logging.info(f"PDF desencriptado con contraseña: '{pwd if pwd else '[vacía]'}'")
                    success = True
                    break
            except Exception as e:
                logging.warning(f"Error intentando contraseña '{pwd}': {e}")

        if not success:
            raise ValueError(
                "No se pudo quitar la contraseña. El PDF está fuertemente protegido o requiere una contraseña específica."
            )

    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    with open(output_path, "wb") as f:
        writer.write(f)

    logging.info(f"PDF desencriptado guardado en: {output_path}")


def split_pdf_selected_pages(pdf_path, output_dir, page_indexes):
    reader = PdfReader(pdf_path)
    for idx in page_indexes:
        if 0 <= idx < len(reader.pages):
            writer = PdfWriter()
            writer.add_page(reader.pages[idx])
            out_path = os.path.join(output_dir, f"page_{idx + 1}.pdf")
            with open(out_path, "wb") as f:
                writer.write(f)
    logging.info(f"PDF dividido (páginas seleccionadas) en: {output_dir}")


def merge_pdfs(pdf_list, output_path):
    merger = PdfMerger()
    for pdf in pdf_list:
        merger.append(pdf)
    merger.write(output_path)
    merger.close()
    logging.info(f"PDFs unidos en: {output_path}")


def split_pdf(pdf_path, output_dir):
    reader = PdfReader(pdf_path)
    for i, page in enumerate(reader.pages):
        writer = PdfWriter()
        writer.add_page(page)
        out_path = os.path.join(output_dir, f"page_{i + 1}.pdf")
        with open(out_path, "wb") as f:
            writer.write(f)
    logging.info(f"PDF dividido en: {output_dir}")


def pdf_to_images(pdf_path, output_dir, image_format="png"):
    image_format = (image_format or "png").lower()
    if image_format not in {"png", "jpg", "jpeg"}:
        raise ValueError("Formato de imagen no soportado. Usa PNG o JPG.")

    pil_format = "PNG" if image_format == "png" else "JPEG"
    output_suffix = ".png" if image_format == "png" else ".jpg"

    paths = []
    first_error = None

    try:
        from pdf2image import convert_from_path

        poppler_path = _resolve_poppler_path()
        images = convert_from_path(pdf_path, poppler_path=poppler_path)
        for i, img in enumerate(images):
            out_path = os.path.join(output_dir, f"page_{i + 1}{output_suffix}")
            if pil_format == "JPEG":
                img = img.convert("RGB")
            img.save(out_path, pil_format)
            paths.append(out_path)

        logging.info(f"PDF convertido a imágenes con pdf2image en: {output_dir}")
        return paths
    except Exception as e:
        first_error = e
        logging.warning(f"pdf2image falló, intentando fallback con PyMuPDF: {e}")

    if PYMUPDF_AVAILABLE:
        doc = fitz.open(pdf_path)
        for i, page in enumerate(doc):
            pix = page.get_pixmap(dpi=200)
            out_path = os.path.join(output_dir, f"page_{i + 1}{output_suffix}")
            pix.save(out_path)
            paths.append(out_path)
        doc.close()
        logging.info(f"PDF convertido a imágenes con PyMuPDF en: {output_dir}")
        return paths

    raise RuntimeError(
        "No se pudo convertir el PDF a imágenes. "
        "Instala Poppler (y define POPPLER_PATH) o instala PyMuPDF. "
        f"Detalle original: {first_error}"
    )


def images_to_pdf(image_paths, output_path):
    images = [Image.open(p).convert("RGB") for p in image_paths]
    images[0].save(output_path, save_all=True, append_images=images[1:])
    logging.info(f"Imágenes convertidas a PDF: {output_path}")


def compress_pdf_to_max_kb(pdf_path, output_path, max_kb=100):
    return compress_pdf_to_max_kb_with_progress(pdf_path, output_path, max_kb=max_kb, progress_callback=None)


def compress_pdf_to_max_kb_with_progress(pdf_path, output_path, max_kb=100, progress_callback=None):
    if not PYMUPDF_AVAILABLE:
        raise RuntimeError("Para comprimir PDF por tamaño máximo se requiere PyMuPDF.")

    max_bytes = int(max_kb) * 1024
    if max_bytes <= 0:
        raise ValueError("El tamaño máximo debe ser mayor que 0 KB")

    if progress_callback:
        progress_callback(5, "Validando archivo")

    try:
        input_size = os.path.getsize(pdf_path)
    except OSError:
        input_size = None

    if input_size is not None and input_size <= max_bytes:
        shutil.copy2(pdf_path, output_path)
        final_kb = round(input_size / 1024, 2)
        if progress_callback:
            progress_callback(100, "Ya cumplía el tamaño objetivo")
        return output_path, final_kb

    if progress_callback:
        progress_callback(15, "Intentando optimización rápida")

    try:
        quick_doc = fitz.open(pdf_path)
        quick_doc.save(output_path, garbage=4, clean=True, deflate=True)
        quick_doc.close()
        quick_size = os.path.getsize(output_path)
        if quick_size <= max_bytes:
            final_kb = round(quick_size / 1024, 2)
            if progress_callback:
                progress_callback(100, "Optimización rápida completada")
            logging.info(f"PDF optimizado sin rasterizar: {output_path} ({final_kb}KB)")
            return output_path, final_kb
    except Exception as e:
        logging.warning(f"Optimización rápida falló, usando fallback raster: {e}")

    best_size = None
    best_tmp_pdf = None
    temp_root = tempfile.mkdtemp(prefix="pdf_compress_")

    dpis = [120, 96, 72]
    qualities = [70, 55, 45]

    total_candidates = len(dpis) * len(qualities)
    candidate_index = 0

    try:
        for dpi in dpis:
            for quality in qualities:
                candidate_index += 1
                if progress_callback:
                    progress = 20 + int((candidate_index / total_candidates) * 70)
                    progress_callback(progress, f"Probando dpi={dpi}, calidad={quality}")

                doc = fitz.open(pdf_path)
                image_paths = []
                candidate_pdf_path = os.path.join(temp_root, f"cand_{dpi}_{quality}.pdf")

                try:
                    for page_number, page in enumerate(doc):
                        pix = page.get_pixmap(dpi=dpi, alpha=False)
                        image_path = os.path.join(temp_root, f"p_{dpi}_{quality}_{page_number}.jpg")
                        pix.save(image_path)
                        image_paths.append(image_path)
                finally:
                    doc.close()

                if not image_paths:
                    continue

                images = [Image.open(path).convert("RGB") for path in image_paths]
                first = images[0]
                rest = images[1:]
                first.save(
                    candidate_pdf_path,
                    format="PDF",
                    save_all=True,
                    append_images=rest,
                    quality=quality,
                    optimize=True,
                    resolution=dpi,
                )

                for img in images:
                    img.close()

                size = os.path.getsize(candidate_pdf_path)

                if best_size is None or size < best_size:
                    best_size = size
                    best_tmp_pdf = candidate_pdf_path

                if size <= max_bytes:
                    shutil.copy2(candidate_pdf_path, output_path)
                    final_kb = round(size / 1024, 2)
                    if progress_callback:
                        progress_callback(100, "Compresión completada")
                    logging.info(f"PDF comprimido a <= {max_kb}KB: {output_path} ({final_kb}KB)")
                    return output_path, final_kb

        if best_tmp_pdf is None:
            raise RuntimeError("No se pudo generar un PDF comprimido")

        shutil.copy2(best_tmp_pdf, output_path)
        final_kb = round((best_size or 0) / 1024, 2)
        if progress_callback:
            progress_callback(100, "Mejor resultado disponible")
        logging.info(f"No se alcanzó {max_kb}KB exactos. Mejor resultado: {output_path} ({final_kb}KB)")
        return output_path, final_kb
    finally:
        try:
            shutil.rmtree(temp_root, ignore_errors=True)
        except Exception:
            pass
