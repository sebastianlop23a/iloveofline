"""
image_service.py - Image conversion and processing service
"""
from PIL import Image
import os
from io import BytesIO
from utils.logger import logging

class ImageService:
    @staticmethod
    def convert_image(input_path, output_path, format):
        with Image.open(input_path) as img:
            img.save(output_path, format=format)
        logging.info(f"Imagen convertida: {output_path}")

    @staticmethod
    def resize_image(input_path, output_path, size):
        with Image.open(input_path) as img:
            img = img.resize(size)
            img.save(output_path)
        logging.info(f"Imagen redimensionada: {output_path}")

    @staticmethod
    def compress_image(input_path, output_path, quality=70):
        with Image.open(input_path) as img:
            img.save(output_path, quality=quality, optimize=True)
        logging.info(f"Imagen comprimida: {output_path}")

    @staticmethod
    def compress_image_to_max_kb(input_path, output_path, max_kb=100):
        max_bytes = int(max_kb) * 1024
        if max_bytes <= 0:
            raise ValueError("El tamaño máximo debe ser mayor que 0 KB")

        with Image.open(input_path) as original:
            image = original.convert("RGB")

        width, height = image.size
        best_bytes = None
        best_blob = None

        for scale in [1.0, 0.9, 0.8, 0.7, 0.6, 0.5]:
            resized = image
            if scale < 1.0:
                resized = image.resize((max(1, int(width * scale)), max(1, int(height * scale))), Image.Resampling.LANCZOS)

            for quality in range(95, 14, -5):
                temp = BytesIO()
                resized.save(temp, format="JPEG", quality=quality, optimize=True)
                data = temp.getvalue()
                size_bytes = len(data)

                if best_bytes is None or size_bytes < best_bytes:
                    best_bytes = size_bytes
                    best_blob = data

                if size_bytes <= max_bytes:
                    with open(output_path, "wb") as f:
                        f.write(data)
                    logging.info(f"Imagen comprimida a <= {max_kb}KB: {output_path} ({size_bytes / 1024:.1f}KB)")
                    return output_path, round(size_bytes / 1024, 2)

        with open(output_path, "wb") as f:
            f.write(best_blob)
        final_kb = round((best_bytes or 0) / 1024, 2)
        logging.info(f"No se alcanzó {max_kb}KB exactos. Mejor resultado: {output_path} ({final_kb}KB)")
        return output_path, final_kb
