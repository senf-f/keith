from unittest.mock import patch

import pytest

from keith.commands import CommandHandler
from keith.repl import HELP_TEXT, Commands


@pytest.fixture
def commands(db):
    return Commands(CommandHandler(db))


def test_help_mentions_every_command(commands):
    missing = [name for name in commands.names if name not in HELP_TEXT]
    assert missing == []


def test_dispatch_runs_no_arg_command(commands, capsys):
    with patch("builtins.input", return_value="Orthodoxy"):
        commands.dispatch("book new")
    assert "Created book 'Orthodoxy'" in capsys.readouterr().out


def test_dispatch_passes_arguments(commands, capsys):
    commands.dispatch("search")
    assert "Usage: search" in capsys.readouterr().out
    commands.dispatch("search nothing-here")
    assert "No results found." in capsys.readouterr().out


def test_dispatch_rejects_unknown_and_stray_arguments(commands, capsys):
    commands.dispatch("frobnicate")
    assert "Unknown command: frobnicate" in capsys.readouterr().out
    commands.dispatch("book new extra")
    assert "Unknown command: book new extra" in capsys.readouterr().out
