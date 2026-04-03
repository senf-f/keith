import os
import sys
import tempfile
from unittest.mock import patch

from keith.editor import open_editor, get_editor_command


def test_get_editor_from_env():
    with patch.dict(os.environ, {"EDITOR": "nano"}):
        assert get_editor_command() == "nano"


def test_get_editor_fallback_windows():
    with patch.dict(os.environ, {}, clear=True):
        env = {k: v for k, v in os.environ.items() if k not in ("EDITOR", "VISUAL")}
        with patch.dict(os.environ, env, clear=True):
            with patch("sys.platform", "win32"):
                assert get_editor_command() == "notepad"


def test_get_editor_fallback_unix():
    with patch.dict(os.environ, {}, clear=True):
        env = {k: v for k, v in os.environ.items() if k not in ("EDITOR", "VISUAL")}
        with patch.dict(os.environ, env, clear=True):
            with patch("sys.platform", "linux"):
                assert get_editor_command() == "vi"


def test_open_editor_returns_content():
    """Test that open_editor reads back the temp file content after editor closes."""
    def fake_editor(cmd, **kwargs):
        filepath = cmd[-1] if isinstance(cmd, list) else cmd.split()[-1]
        with open(filepath, "w") as f:
            f.write("Hello from editor")
        return None

    with patch("keith.editor.subprocess.call", side_effect=fake_editor):
        content = open_editor()
    assert content == "Hello from editor"


def test_open_editor_with_initial_content():
    """Test that existing content is pre-filled in the temp file."""
    def fake_editor(cmd, **kwargs):
        filepath = cmd[-1] if isinstance(cmd, list) else cmd.split()[-1]
        with open(filepath, "r") as f:
            initial = f.read()
        assert initial == "Existing text"
        with open(filepath, "w") as f:
            f.write("Updated text")
        return None

    with patch("keith.editor.subprocess.call", side_effect=fake_editor):
        content = open_editor(initial_content="Existing text")
    assert content == "Updated text"
