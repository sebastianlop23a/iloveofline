import os


def extract_dropped_paths(mime_data):
    if mime_data is None or not mime_data.hasUrls():
        return []

    paths = []
    for url in mime_data.urls():
        if not url.isLocalFile():
            continue
        local_path = os.path.abspath(url.toLocalFile())
        if local_path and local_path not in paths:
            paths.append(local_path)
    return paths


def filter_existing_files(paths, allowed_extensions=None):
    normalized_extensions = None
    if allowed_extensions:
        normalized_extensions = tuple(ext.lower() for ext in allowed_extensions)

    valid_files = []
    for path in paths or []:
        if not os.path.isfile(path):
            continue
        if normalized_extensions and not path.lower().endswith(normalized_extensions):
            continue
        valid_files.append(path)
    return valid_files


def filter_existing_directories(paths):
    valid_dirs = []
    for path in paths or []:
        if os.path.isdir(path):
            valid_dirs.append(path)
    return valid_dirs
