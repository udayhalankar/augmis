import os
import tempfile


def write_temp_connector_file(file_name: str, content: bytes) -> str:
    suffix = os.path.splitext(file_name or "")[1]

    temp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    temp.write(content)
    temp.flush()
    temp.close()

    return temp.name


def safe_remove_temp_file(path: str | None):
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass
