"""
history_service.py - Service for querying and managing history records
"""
import os
from database.db import get_connection
from utils.logger import logging

class HistoryService:
    @staticmethod
    def get_history(limit=100):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, action, file_name, timestamp FROM history ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        return rows

    @staticmethod
    def clear_history():
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM history")
        conn.commit()
        conn.close()
        logging.info("Historial limpiado")

    @staticmethod
    def get_created_files(limit=500):
        rows = HistoryService.get_history(limit=limit)
        files = []
        seen = set()

        for _id, action, file_name, timestamp in rows:
            if not file_name:
                continue

            normalized = os.path.normpath(file_name)

            if os.path.isfile(normalized):
                key = os.path.normcase(os.path.abspath(normalized))
                if key in seen:
                    continue
                seen.add(key)
                files.append(
                    {
                        "action": action,
                        "path": os.path.abspath(normalized),
                        "name": os.path.basename(normalized),
                        "timestamp": timestamp,
                    }
                )
                continue

            if os.path.isdir(normalized):
                for root, _, filenames in os.walk(normalized):
                    for filename in filenames:
                        full_path = os.path.abspath(os.path.join(root, filename))
                        key = os.path.normcase(full_path)
                        if key in seen:
                            continue
                        seen.add(key)
                        files.append(
                            {
                                "action": action,
                                "path": full_path,
                                "name": filename,
                                "timestamp": timestamp,
                            }
                        )

        files.sort(key=lambda item: item.get("timestamp") or "", reverse=True)
        return files
