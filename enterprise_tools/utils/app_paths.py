"""
app_paths.py - Centralized app folders for generated documents
"""

import os
import platform
import ctypes
from ctypes import wintypes
from pathlib import Path


APP_FOLDER_NAME = "enterprise_tools"


def _get_windows_documents_dir() -> Path | None:
    if platform.system() != "Windows":
        return None

    try:
        FOLDERID_Documents = ctypes.c_char_p(b"{FDD39AD0-238F-46AF-ADB4-6C85480369C7}")

        class GUID(ctypes.Structure):
            _fields_ = [
                ("Data1", wintypes.DWORD),
                ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD),
                ("Data4", ctypes.c_ubyte * 8),
            ]

        def guid_from_string(guid_string: str) -> GUID:
            import uuid

            u = uuid.UUID(guid_string)
            data4 = (ctypes.c_ubyte * 8).from_buffer_copy(u.bytes[8:])
            return GUID(u.time_low, u.time_mid, u.time_hi_version, data4)

        guid = guid_from_string("{FDD39AD0-238F-46AF-ADB4-6C85480369C7}")

        SHGetKnownFolderPath = ctypes.windll.shell32.SHGetKnownFolderPath
        SHGetKnownFolderPath.argtypes = [ctypes.POINTER(GUID), wintypes.DWORD, wintypes.HANDLE, ctypes.POINTER(ctypes.c_wchar_p)]
        SHGetKnownFolderPath.restype = wintypes.HRESULT

        path_ptr = ctypes.c_wchar_p()
        result = SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(path_ptr))
        if result != 0 or not path_ptr.value:
            return None

        documents_path = Path(path_ptr.value)
        ctypes.windll.ole32.CoTaskMemFree(path_ptr)
        return documents_path
    except Exception:
        return None


def get_app_home() -> str:
    env_home = os.environ.get("ENTERPRISE_TOOLS_HOME")
    if env_home:
        path = Path(env_home).expanduser().resolve()
    else:
        documents_dir = _get_windows_documents_dir()
        if documents_dir is None:
            fallback_docs = Path.home() / "Documents"
            documents_dir = fallback_docs if fallback_docs.exists() else Path.home()

        base_dir = documents_dir
        path = base_dir / APP_FOLDER_NAME

    path.mkdir(parents=True, exist_ok=True)
    normalized = str(path)
    os.environ["ENTERPRISE_TOOLS_HOME"] = normalized
    return normalized


def get_output_dir(category: str) -> str:
    folder = Path(get_app_home()) / category
    folder.mkdir(parents=True, exist_ok=True)
    return str(folder)


def ensure_in_output_dir(path: str, category: str) -> str:
    output_dir = get_output_dir(category)
    base_name = os.path.basename(path)
    return os.path.join(output_dir, base_name)
