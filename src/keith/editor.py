import os
import shlex
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


def editor_argv(editor: str) -> list[str]:
    # $EDITOR may carry arguments ("code --wait"). Windows paths keep their
    # backslashes, so split there without POSIX escaping and strip the quotes.
    if sys.platform == "win32":
        return [part.strip('"') for part in shlex.split(editor, posix=False)]
    return shlex.split(editor)


def open_editor(initial_content: str = "") -> str | None:
    """Return the edited text, or None if the editor couldn't run or failed."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(initial_content)
        tmp_path = tmp.name

    try:
        try:
            returncode = subprocess.call(editor_argv(get_editor_command()) + [tmp_path])
        except OSError:
            return None
        if returncode != 0:
            return None
        with open(tmp_path, "r", encoding="utf-8") as f:
            content = f.read()
        return content
    finally:
        os.unlink(tmp_path)
