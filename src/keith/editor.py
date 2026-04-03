import os
import subprocess
import sys
import tempfile


def get_editor_command() -> str:
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")
    if editor:
        return editor
    if sys.platform == "win32":
        return "notepad"
    return "vi"


def open_editor(initial_content: str = "") -> str | None:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(initial_content)
        tmp_path = tmp.name

    try:
        editor = get_editor_command()
        subprocess.call([editor, tmp_path])
        with open(tmp_path, "r", encoding="utf-8") as f:
            content = f.read()
        return content
    finally:
        os.unlink(tmp_path)
