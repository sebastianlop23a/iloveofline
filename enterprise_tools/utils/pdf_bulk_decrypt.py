import os
import logging
import shutil
import subprocess
from io import BytesIO
from pypdf import PdfReader, PdfWriter

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def quitar_contraseña_apertura_pdf(archivo_entrada, archivo_salida, password=None):
    """
    Quita la contraseña de apertura de un PDF.
    Retorna True si se pudo procesar.
    """

    try:
        # ===== 1. Intentar con QPDF =====
        qpdf_path = shutil.which("qpdf")

        if qpdf_path and password:
            cmd = [qpdf_path, f"--password={password}", "--decrypt", archivo_entrada, archivo_salida]
            result = subprocess.run(cmd, capture_output=True)

            if result.returncode == 0 and os.path.exists(archivo_salida):
                logging.info(f"QPDF desencriptó: {archivo_entrada}")
                return True
            else:
                logging.warning(f"QPDF falló con contraseña en {archivo_entrada}")

        # ===== 2. Fallback con pypdf =====
        reader = PdfReader(archivo_entrada)

        if reader.is_encrypted:
            if password:
                if not reader.decrypt(password):
                    logging.warning("Contraseña incorrecta")
                    return False
            else:
                logging.warning("PDF encriptado y no se proporcionó contraseña")
                return False

        writer = PdfWriter()

        for page in reader.pages:
            writer.add_page(page)

        if reader.metadata:
            writer.add_metadata(reader.metadata)

        with open(archivo_salida, "wb") as f:
            writer.write(f)

        logging.info(f"PyPDF reconstruyó: {archivo_entrada}")
        return True

    except Exception as e:
        logging.error(f"Error procesando {archivo_entrada}: {e}")
        return False


def remove_weak_pdf_protection_in_folder(folder_path):
    processed = 0
    failed = 0

    for filename in os.listdir(folder_path):
        if not filename.lower().endswith(".pdf"):
            continue

        file_path = os.path.join(folder_path, filename)
        temp_out = file_path + ".tmp"

        try:
            # ===== 1. Intentar QPDF sin contraseña =====
            qpdf_path = shutil.which("qpdf")

            if qpdf_path:
                cmd = [qpdf_path, "--decrypt", file_path, temp_out]
                result = subprocess.run(cmd, capture_output=True)

                if result.returncode == 0 and os.path.exists(temp_out):
                    shutil.move(temp_out, file_path)
                    processed += 1
                    logging.info(f"QPDF quitó restricciones: {filename}")
                    continue

            # ===== 2. Fallback PyPDF =====
            reader = PdfReader(file_path)
            writer = PdfWriter()

            if reader.is_encrypted:
                passwords = ["", "owner", "user", "1234", "12345", "password", "admin"]
                for pwd in passwords:
                    try:
                        if reader.decrypt(pwd):
                            break
                    except Exception:
                        pass

            for page in reader.pages:
                writer.add_page(page)

            if reader.metadata:
                writer.add_metadata(reader.metadata)

            with open(file_path, "wb") as f:
                writer.write(f)

            processed += 1
            logging.info(f"PyPDF reconstruyó: {filename}")

        except Exception as e:
            failed += 1
            logging.error(f"No se pudo procesar {filename}: {e}")

    print(f"Procesados: {processed}, Fallidos: {failed}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Quita protecciones débiles de PDFs en una carpeta")
    parser.add_argument("carpeta", help="Ruta de la carpeta")
    args = parser.parse_args()

    remove_weak_pdf_protection_in_folder(args.carpeta)