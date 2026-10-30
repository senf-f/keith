import io

from click.testing import CliRunner

from keith.cli import main
from keith.db import Database
from keith.models import PUBLISHED


def test_list_marks_drafts_like_the_repl(tmp_path, monkeypatch):
    path = tmp_path / "keith.db"
    monkeypatch.setenv("KEITH_DB", str(path))
    db = Database(path)
    db.create_book("Draft Book")
    done = db.create_book("Done Book")
    db.set_status(done.id, PUBLISHED)
    db.close()

    out = CliRunner().invoke(main, ["list"]).output
    assert "Draft Book" in out and "draft" in out.splitlines()[0]
    assert "draft" not in out.splitlines()[1]


def test_export_unknown_book(tmp_path, monkeypatch):
    monkeypatch.setenv("KEITH_DB", str(tmp_path / "keith.db"))
    out = CliRunner().invoke(main, ["export", "99"]).output
    assert "Book with id 99 not found." in out


def test_cli_pull_obsidian(tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "a.md").write_text("an untagged thought", encoding="utf-8")
    monkeypatch.setenv("KEITH_DB", str(tmp_path / "keith.db"))
    monkeypatch.setenv("KEITH_OBSIDIAN_INBOX", str(vault))
    monkeypatch.delenv("KEITH_TELEGRAM_TOKEN", raising=False)
    monkeypatch.delenv("KEITH_TELEGRAM_USER", raising=False)
    out = CliRunner().invoke(main, ["pull", "obsidian"]).output
    assert "went to Inbox" in out


def test_unencodable_output_is_replaced_not_raised(monkeypatch):
    from keith.cli import _tolerate_unencodable_output

    out = io.TextIOWrapper(io.BytesIO(), encoding="cp1250")
    monkeypatch.setattr("sys.stdout", out)
    monkeypatch.setattr("sys.stderr", out)
    _tolerate_unencodable_output()
    out.write("a → b")
    out.flush()
    assert out.buffer.getvalue().startswith(b"a ")
