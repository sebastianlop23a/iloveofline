"""
task_manager_service.py - Métricas del sistema, recomendaciones y optimización segura
"""

import gc
import os
import shutil
import sys
import time
import ctypes
import subprocess
from pathlib import Path

if __package__ is None or __package__ == "":
    package_root = Path(__file__).resolve().parent.parent
    package_root_str = str(package_root)
    if package_root_str not in sys.path:
        sys.path.insert(0, package_root_str)

from utils.app_paths import get_app_home
from utils.logger import logging

try:
    import psutil
except Exception:
    psutil = None


class TaskManagerService:
    _PROTECTED_PROCESS_NAMES = {
        "system",
        "system idle process",
        "wininit.exe",
        "winlogon.exe",
        "services.exe",
        "lsass.exe",
        "csrss.exe",
        "smss.exe",
        "dwm.exe",
        "explorer.exe",
        "svchost.exe",
        "taskhostw.exe",
        "fontdrvhost.exe",
        "registry",
    }

    _COMMON_USER_APP_NAMES = {
        "chrome.exe",
        "msedge.exe",
        "firefox.exe",
        "brave.exe",
        "opera.exe",
        "teams.exe",
        "slack.exe",
        "discord.exe",
        "zoom.exe",
        "notion.exe",
        "telegram.exe",
        "whatsapp.exe",
        "vlc.exe",
    }

    @staticmethod
    def is_available():
        return psutil is not None

    @staticmethod
    def get_system_snapshot():
        app_home = get_app_home()
        snapshot = {
            "cpu_percent": None,
            "ram_percent": None,
            "ram_used_gb": None,
            "ram_total_gb": None,
            "disk_percent": None,
            "disk_free_gb": None,
            "disk_total_gb": None,
            "uptime_seconds": None,
            "platform_available": TaskManagerService.is_available(),
            "app_home": app_home,
        }

        if psutil is not None:
            try:
                snapshot["cpu_percent"] = float(psutil.cpu_percent(interval=0.2))
            except Exception:
                snapshot["cpu_percent"] = 0.0

            try:
                memory = psutil.virtual_memory()
                snapshot["ram_percent"] = float(memory.percent)
                snapshot["ram_used_gb"] = memory.used / (1024 ** 3)
                snapshot["ram_total_gb"] = memory.total / (1024 ** 3)
            except Exception:
                pass

            try:
                disk = psutil.disk_usage(app_home)
                snapshot["disk_percent"] = float(disk.percent)
                snapshot["disk_free_gb"] = disk.free / (1024 ** 3)
                snapshot["disk_total_gb"] = disk.total / (1024 ** 3)
            except Exception:
                try:
                    disk = psutil.disk_usage(str(Path.home()))
                    snapshot["disk_percent"] = float(disk.percent)
                    snapshot["disk_free_gb"] = disk.free / (1024 ** 3)
                    snapshot["disk_total_gb"] = disk.total / (1024 ** 3)
                except Exception:
                    pass

            try:
                snapshot["uptime_seconds"] = max(0, int(time.time() - float(psutil.boot_time())))
            except Exception:
                pass
        else:
            try:
                disk = shutil.disk_usage(app_home)
                snapshot["disk_total_gb"] = disk.total / (1024 ** 3)
                snapshot["disk_free_gb"] = disk.free / (1024 ** 3)
                snapshot["disk_percent"] = (disk.used / max(1, disk.total)) * 100
            except Exception:
                pass

        return snapshot

    @staticmethod
    def get_top_processes(limit=20):
        if psutil is None:
            return []

        processes = []
        total_ram_mb = None

        try:
            try:
                total_ram_mb = psutil.virtual_memory().total / (1024 ** 2)
            except Exception:
                total_ram_mb = None

            for proc in psutil.process_iter(["pid", "name", "status", "memory_percent", "cpu_percent"]):
                try:
                    memory_percent = float(proc.info.get("memory_percent") or 0.0)
                    if total_ram_mb is not None:
                        memory_mb = (memory_percent / 100.0) * total_ram_mb
                    else:
                        memory_mb = 0.0

                    process_item = {
                        "pid": int(proc.info.get("pid") or 0),
                        "name": (proc.info.get("name") or "(sin nombre)")[:48],
                        "status": str(proc.info.get("status") or "desconocido"),
                        "cpu_percent": float(proc.info.get("cpu_percent") or 0.0),
                        "memory_mb": float(memory_mb),
                    }
                    processes.append(process_item)
                except Exception:
                    continue
        except Exception as exc:
            logging.error(f"Error consultando procesos: {exc}")
            return []

        processes.sort(key=lambda item: (item["memory_mb"], item["cpu_percent"]), reverse=True)
        return processes[:limit]

    @staticmethod
    def build_recommendations(snapshot, processes):
        recommendations = []

        cpu_percent = snapshot.get("cpu_percent")
        ram_percent = snapshot.get("ram_percent")
        disk_percent = snapshot.get("disk_percent")

        if cpu_percent is not None and cpu_percent >= 85:
            recommendations.append("CPU alto: cierra procesos con uso elevado de CPU y evita tareas pesadas en paralelo.")
        elif cpu_percent is not None and cpu_percent >= 65:
            recommendations.append("CPU moderado: prioriza una tarea pesada a la vez para mantener fluidez.")

        if ram_percent is not None and ram_percent >= 85:
            recommendations.append("RAM crítica: cierra aplicaciones en segundo plano para evitar lentitud.")
        elif ram_percent is not None and ram_percent >= 70:
            recommendations.append("RAM en uso medio-alto: considera cerrar pestañas o apps que no estés usando.")

        if disk_percent is not None and disk_percent >= 92:
            recommendations.append("Disco casi lleno: libera espacio (descargas, temporales y archivos duplicados).")
        elif disk_percent is not None and disk_percent >= 82:
            recommendations.append("Disco en umbral alto: mantén al menos 15% libre para mejor rendimiento.")

        heavy_processes = [proc for proc in processes if proc.get("memory_mb", 0) >= 700]
        if heavy_processes:
            top_names = ", ".join(proc["name"] for proc in heavy_processes[:3])
            recommendations.append(f"Procesos pesados detectados: {top_names}. Revisa si puedes cerrarlos o reiniciarlos.")

        if not recommendations:
            recommendations.append("Estado saludable: el equipo no muestra cuellos de botella críticos por ahora.")

        recommendations.append("Tip: usa 'Optimizar equipo' para limpieza segura de temporales y refrescar el diagnóstico.")
        return recommendations

    @staticmethod
    def optimize_system():
        app_home = Path(get_app_home())
        temp_root = os.environ.get("TEMP", "")
        before_snapshot = TaskManagerService.get_system_snapshot()

        cleanup_targets = [
            (app_home / "temp", 24 * 3600),
            (app_home / "cache", 24 * 3600),
            (app_home / "tmp", 24 * 3600),
            (app_home / "logs", 30 * 24 * 3600),
        ]

        if temp_root:
            cleanup_targets.append((Path(temp_root) / "enterprise_tools", 24 * 3600))

        removed_files = 0
        removed_dirs = 0
        freed_bytes = 0
        details = []

        for folder, max_age_seconds in cleanup_targets:
            result = TaskManagerService._cleanup_folder(folder, max_age_seconds=max_age_seconds)
            removed_files += result["removed_files"]
            removed_dirs += result["removed_dirs"]
            freed_bytes += result["freed_bytes"]
            if result["removed_files"] > 0 or result["removed_dirs"] > 0:
                details.append(
                    f"{folder}: {result['removed_files']} archivos y {result['removed_dirs']} carpetas"
                )

        if temp_root:
            broad_temp_result = TaskManagerService._cleanup_folder(
                Path(temp_root),
                max_age_seconds=3 * 24 * 3600,
                predicate=TaskManagerService._is_temp_artifact,
                max_entries=12000,
            )
            removed_files += broad_temp_result["removed_files"]
            removed_dirs += broad_temp_result["removed_dirs"]
            freed_bytes += broad_temp_result["freed_bytes"]

            if broad_temp_result["removed_files"] > 0 or broad_temp_result["removed_dirs"] > 0:
                details.append(
                    f"TEMP usuario: {broad_temp_result['removed_files']} archivos y "
                    f"{broad_temp_result['removed_dirs']} carpetas temporales"
                )

        gc_objects = gc.collect()
        details.append(f"GC ejecutado: {gc_objects} objetos recolectados")

        memory_result = TaskManagerService._release_memory_pressure()
        if memory_result.get("trim_supported"):
            details.append(
                "RAM compactada: "
                f"{memory_result['trimmed_processes']}/{memory_result['trim_attempted']} procesos"
            )
        else:
            details.append("RAM compactada: no disponible en este sistema.")

        after_snapshot = TaskManagerService.get_system_snapshot()
        ram_before = before_snapshot.get("ram_percent")
        ram_after = after_snapshot.get("ram_percent")
        ram_delta = None
        if ram_before is not None and ram_after is not None:
            ram_delta = ram_before - ram_after
            details.append(
                f"RAM antes/después: {ram_before:.1f}% → {ram_after:.1f}% "
                f"(delta {ram_delta:+.1f} pp)"
            )

        freed_mb = freed_bytes / (1024 ** 2)
        summary = (
            f"Optimización completada. Liberado disco aprox: {freed_mb:.2f} MB | "
            f"Archivos removidos: {removed_files}"
        )
        if ram_delta is not None:
            summary += f" | RAM: {ram_before:.1f}%→{ram_after:.1f}%"

        logging.info(summary)
        return {
            "summary": summary,
            "removed_files": removed_files,
            "removed_dirs": removed_dirs,
            "freed_bytes": freed_bytes,
            "details": details,
        }

    @staticmethod
    def _cleanup_folder(folder: Path, max_age_seconds=24 * 3600, predicate=None, max_entries=None):
        if not folder.exists() or not folder.is_dir():
            return {"removed_files": 0, "removed_dirs": 0, "freed_bytes": 0}

        now = time.time()
        removed_files = 0
        removed_dirs = 0
        freed_bytes = 0
        reviewed_entries = 0

        for path in sorted(folder.rglob("*"), reverse=True):
            if max_entries is not None and reviewed_entries >= max_entries:
                break

            reviewed_entries += 1

            try:
                if predicate is not None and not predicate(path):
                    continue

                if path.is_file():
                    age_seconds = now - path.stat().st_mtime
                    if age_seconds < max_age_seconds:
                        continue
                    file_size = path.stat().st_size
                    path.unlink(missing_ok=True)
                    removed_files += 1
                    freed_bytes += max(0, file_size)
                elif path.is_dir():
                    if any(path.iterdir()):
                        continue
                    path.rmdir()
                    removed_dirs += 1
            except Exception:
                continue

        return {
            "removed_files": removed_files,
            "removed_dirs": removed_dirs,
            "freed_bytes": freed_bytes,
        }

    @staticmethod
    def _is_temp_artifact(path: Path):
        name = path.name.lower()
        temp_extensions = {
            ".tmp",
            ".temp",
            ".old",
            ".bak",
            ".dmp",
            ".etl",
            ".log",
            ".gid",
            ".chk",
        }

        if path.is_file():
            return (
                path.suffix.lower() in temp_extensions
                or name.startswith("tmp")
                or name.startswith("~")
            )

        if path.is_dir():
            return any(token in name for token in ("temp", "tmp", "cache", "enterprise_tools"))

        return False

    @staticmethod
    def _release_memory_pressure():
        result = {
            "trim_supported": False,
            "trim_attempted": 0,
            "trimmed_processes": 0,
        }

        if os.name != "nt":
            return result

        try:
            import ctypes
            from ctypes import wintypes
        except Exception:
            return result

        result["trim_supported"] = True

        PROCESS_QUERY_INFORMATION = 0x0400
        PROCESS_SET_QUOTA = 0x0100
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        desired_access = PROCESS_QUERY_INFORMATION | PROCESS_SET_QUOTA | PROCESS_QUERY_LIMITED_INFORMATION

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi_dll = ctypes.WinDLL("psapi", use_last_error=True)

        open_process = kernel32.OpenProcess
        open_process.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        open_process.restype = wintypes.HANDLE

        close_handle = kernel32.CloseHandle
        close_handle.argtypes = [wintypes.HANDLE]
        close_handle.restype = wintypes.BOOL

        empty_working_set = psapi_dll.EmptyWorkingSet
        empty_working_set.argtypes = [wintypes.HANDLE]
        empty_working_set.restype = wintypes.BOOL

        own_pid = os.getpid()
        candidate_pids = [own_pid]

        if psutil is not None:
            own_user = None
            try:
                own_user = psutil.Process(own_pid).username()
            except Exception:
                own_user = None

            process_candidates = []
            for proc in psutil.process_iter(["pid", "name", "username", "memory_percent"]):
                try:
                    pid = int(proc.info.get("pid") or 0)
                    if pid <= 4 or pid == own_pid:
                        continue

                    username = proc.info.get("username")
                    if own_user and username and username != own_user:
                        continue

                    memory_percent = float(proc.info.get("memory_percent") or 0.0)
                    process_candidates.append((memory_percent, pid))
                except Exception:
                    continue

            process_candidates.sort(key=lambda item: item[0], reverse=True)
            candidate_pids.extend(pid for _, pid in process_candidates[:30])

        seen_pids = set()
        for pid in candidate_pids:
            if pid in seen_pids:
                continue
            seen_pids.add(pid)

            handle = open_process(desired_access, False, int(pid))
            if not handle:
                continue

            result["trim_attempted"] += 1
            try:
                if empty_working_set(handle):
                    result["trimmed_processes"] += 1
            except Exception:
                pass
            finally:
                close_handle(handle)

        return result

    @staticmethod
    def _try_windll_terminate(pid):
        """Intenta terminar proceso usando Windows kernel32 API."""
        try:
            handle = ctypes.windll.kernel32.OpenProcess(1, False, pid)
            if handle:
                result = ctypes.windll.kernel32.TerminateProcess(handle, 0)
                ctypes.windll.kernel32.CloseHandle(handle)
                return result != 0
        except Exception:
            pass
        return False

    @staticmethod
    def _try_taskkill_elevate(pid, force=False):
        """Intenta terminar proceso usando taskkill de Windows con elevación."""
        try:
            cmd = ["taskkill", "/PID", str(pid)]
            if force:
                cmd.append("/F")
            subprocess.run(cmd, capture_output=True, timeout=5)
            return True
        except Exception:
            pass
        return False

    @staticmethod
    def terminate_process(pid):
        """Finaliza un proceso con múltiples estrategias de fallback para permisos."""
        if psutil is None:
            return False, "psutil no está disponible en este entorno."

        try:
            pid = int(pid)
        except Exception:
            return False, "PID inválido."

        if pid <= 4:
            return False, "No es seguro finalizar procesos críticos del sistema."

        if pid == os.getpid():
            return False, "No puedes finalizar el proceso actual de la aplicación."

        try:
            proc = psutil.Process(pid)
            name = proc.name()
        except Exception:
            return False, "No se puede acceder a información del proceso."

        # Estrategia 1: terminate() con espera
        try:
            proc.terminate()
            try:
                proc.wait(timeout=2)
                return True, f"Proceso finalizado: {name} (PID {pid})."
            except psutil.TimeoutExpired:
                pass
        except psutil.AccessDenied:
            pass  # Continuar con siguiente estrategia
        except psutil.NoSuchProcess:
            return False, "El proceso ya no existe."
        except Exception:
            pass

        # Estrategia 2: kill() con psutil
        try:
            proc.kill()
            try:
                proc.wait(timeout=2)
                return True, f"Proceso forzado (kill): {name} (PID {pid})."
            except psutil.TimeoutExpired:
                pass
        except psutil.AccessDenied:
            pass  # Continuar con siguiente estrategia
        except psutil.NoSuchProcess:
            return False, "El proceso ya no existe."
        except Exception:
            pass

        # Estrategia 3: Windows kernel32 API
        if os.name == "nt":
            if TaskManagerService._try_windll_terminate(pid):
                return True, f"Proceso terminado (WinAPI): {name} (PID {pid})."

        # Estrategia 4: taskkill sin fuerza
        if os.name == "nt":
            if TaskManagerService._try_taskkill_elevate(pid, force=False):
                try:
                    # Verificar si realmente se cerró
                    proc.wait(timeout=1)
                    return True, f"Proceso terminado (taskkill): {name} (PID {pid})."
                except Exception:
                    pass

        # Estrategia 5: taskkill con fuerza /F
        if os.name == "nt":
            if TaskManagerService._try_taskkill_elevate(pid, force=True):
                return True, f"Proceso terminado a la fuerza (taskkill /F): {name} (PID {pid})."

        return False, f"No se pudo finalizar '{name}' (PID {pid}): acceso denegado o privilegios insuficientes."

    @staticmethod
    def terminate_heavy_processes_legacy(pid):
        """Legacy: Finaliza un proceso usando el método anterior (para referencia)."""
        """Deprecated, use terminate_process instead."""
        if psutil is None:
            return False, "psutil no está disponible en este entorno."

        try:
            pid = int(pid)
        except Exception:
            return False, "PID inválido."

        if pid <= 4:
            return False, "No es seguro finalizar procesos críticos del sistema."

        if pid == os.getpid():
            return False, "No puedes finalizar el proceso actual de la aplicación."

        try:
            proc = psutil.Process(pid)
            name = proc.name()
            proc.terminate()
            try:
                proc.wait(timeout=2)
                return True, f"Proceso finalizado: {name} (PID {pid})."
            except psutil.TimeoutExpired:
                proc.kill()
                return True, f"Proceso forzado: {name} (PID {pid})."
        except psutil.AccessDenied:
            return False, "Acceso denegado para finalizar ese proceso."
        except psutil.NoSuchProcess:
            return False, "El proceso ya no existe."
        except Exception as exc:
            return False, f"No se pudo finalizar el proceso: {exc}"

    @staticmethod
    def terminate_heavy_processes(limit=5, min_memory_mb=700.0):
        if psutil is None:
            return {
                "summary": "psutil no está disponible en este entorno.",
                "terminated": 0,
                "attempted": 0,
                "details": [],
            }

        own_pid = os.getpid()
        own_user = None
        total_ram_mb = None

        try:
            own_user = psutil.Process(own_pid).username()
        except Exception:
            own_user = None

        try:
            total_ram_mb = psutil.virtual_memory().total / (1024 ** 2)
        except Exception:
            total_ram_mb = None

        candidates = []
        for proc in psutil.process_iter(["pid", "name", "username", "memory_percent"]):
            try:
                pid = int(proc.info.get("pid") or 0)
                if pid <= 4 or pid == own_pid:
                    continue

                name = (proc.info.get("name") or "").strip()
                if TaskManagerService._is_protected_process_name(name):
                    continue

                username = proc.info.get("username")
                if own_user and username and username != own_user:
                    continue

                memory_percent = float(proc.info.get("memory_percent") or 0.0)
                if total_ram_mb is None:
                    continue

                memory_mb = (memory_percent / 100.0) * total_ram_mb
                if memory_mb < float(min_memory_mb):
                    continue

                candidates.append({"pid": pid, "name": name or "(sin nombre)", "memory_mb": memory_mb})
            except Exception:
                continue

        candidates.sort(key=lambda item: item["memory_mb"], reverse=True)
        to_terminate = candidates[: max(0, int(limit))]

        terminated = 0
        details = []
        for item in to_terminate:
            ok, message = TaskManagerService.terminate_process(item["pid"])
            details.append(message)
            if ok:
                terminated += 1

        summary = (
            f"Acción completada. Procesos pesados finalizados: {terminated}/{len(to_terminate)} "
            f"(umbral {min_memory_mb:.0f} MB)."
        )
        return {
            "summary": summary,
            "terminated": terminated,
            "attempted": len(to_terminate),
            "details": details,
        }

    @staticmethod
    def terminate_common_user_apps(limit=12):
        if psutil is None:
            return {
                "summary": "psutil no está disponible en este entorno.",
                "terminated": 0,
                "attempted": 0,
                "details": [],
            }

        own_pid = os.getpid()
        own_user = None

        try:
            own_user = psutil.Process(own_pid).username()
        except Exception:
            own_user = None

        candidates = []
        for proc in psutil.process_iter(["pid", "name", "username"]):
            try:
                pid = int(proc.info.get("pid") or 0)
                if pid <= 4 or pid == own_pid:
                    continue

                name = (proc.info.get("name") or "").strip().lower()
                if not name or name not in TaskManagerService._COMMON_USER_APP_NAMES:
                    continue

                if TaskManagerService._is_protected_process_name(name):
                    continue

                username = proc.info.get("username")
                if own_user and username and username != own_user:
                    continue

                candidates.append({"pid": pid, "name": name})
            except Exception:
                continue

        to_terminate = candidates[: max(0, int(limit))]

        terminated = 0
        details = []
        for item in to_terminate:
            ok, message = TaskManagerService.terminate_process(item["pid"])
            details.append(message)
            if ok:
                terminated += 1

        summary = (
            f"Acción completada. Ventanas/apps comunes cerradas: {terminated}/{len(to_terminate)}."
        )
        return {
            "summary": summary,
            "terminated": terminated,
            "attempted": len(to_terminate),
            "details": details,
        }

    @staticmethod
    def _is_protected_process_name(name):
        normalized = (name or "").strip().lower()
        return normalized in TaskManagerService._PROTECTED_PROCESS_NAMES
