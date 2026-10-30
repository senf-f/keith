import io
import urllib.error
import urllib.request

import pytest

from keith.importers import SourceError
from keith.telegram import TelegramSource


class FakeHttp:
    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = []

    def __call__(self, method, params):
        self.calls.append((method, params))
        return self.replies.pop(0)


def msg(update_id, text=None, user=123456789, name="Mate", message_id=None,
        caption=None, date=1767225600, chat=123456789, key="message"):
    message = {
        "message_id": message_id if message_id is not None else update_id * 10,
        "from": {"id": user, "first_name": name},
        "chat": {"id": chat},
        "date": date,
    }
    if text is not None:
        message["text"] = text
    if caption is not None:
        message["caption"] = caption
    return {"update_id": update_id, key: message}


def ok(*updates):
    return {"ok": True, "result": list(updates)}


def test_text_and_caption_become_items():
    http = FakeHttp(ok(msg(5, text="hello"), msg(6, caption="a photo")))
    result = TelegramSource("T", 123456789, http).fetch()
    assert [(i.source, i.key, i.text) for i in result.items] == [
        ("Telegram", "123456789:50", "hello"),
        ("Telegram", "123456789:60", "a photo"),
    ]
    assert http.calls == [("getUpdates", {"timeout": 0, "limit": 100})]


def test_other_senders_and_no_text_counted():
    http = FakeHttp(ok(msg(5, text="hi", user=42), msg(6), msg(7, text="mine")))
    result = TelegramSource("T", 123456789, http).fetch()
    assert [i.text for i in result.items] == ["mine"]
    assert result.skipped == {"other senders": 1, "no text": 1}


def test_edited_messages_ignored():
    http = FakeHttp(ok(msg(5, text="edited", key="edited_message"), msg(6, text="x")))
    result = TelegramSource("T", 123456789, http).fetch()
    assert [i.text for i in result.items] == ["x"]
    assert result.skipped == {}


def test_ack_offset_is_highest_fetched_plus_one():
    http = FakeHttp(ok(*[msg(n, text=f"n{n}") for n in range(5, 105)]), ok())
    source = TelegramSource("T", 123456789, http)
    source.fetch()
    source.acknowledge(set())
    assert http.calls[1] == ("getUpdates", {"offset": 105, "timeout": 0, "limit": 1})
    assert len(http.calls) == 2


def test_ack_covers_skipped_updates():
    http = FakeHttp(ok(msg(5, text="a"), msg(6, text="b", user=1), msg(7, text="c", key="edited_message")), ok())
    source = TelegramSource("T", 123456789, http)
    source.fetch()
    source.acknowledge(set())
    assert http.calls[1][1]["offset"] == 8


def test_ack_stops_before_first_failure():
    http = FakeHttp(ok(*[msg(n, text=f"n{n}") for n in range(5, 10)]), ok())
    source = TelegramSource("T", 123456789, http)
    result = source.fetch()
    failed = {i.key for i in result.items if i.text in ("n7", "n9")}
    source.acknowledge(failed)
    assert http.calls[1][1]["offset"] == 7


def test_no_ack_call_when_nothing_fetched():
    http = FakeHttp(ok())
    source = TelegramSource("T", 123456789, http)
    source.fetch()
    source.acknowledge(set())
    assert len(http.calls) == 1


def test_first_run_lists_senders_and_does_not_ack():
    http = FakeHttp(ok(msg(5, text="a"), msg(6, text="b")))
    source = TelegramSource("T", None, http)
    with pytest.raises(SourceError) as info:
        source.fetch()
    text = str(info.value)
    assert "set KEITH_TELEGRAM_USER to import. Senders waiting:" in text
    assert "  123456789  Mate (2 messages)" in text
    assert len(http.calls) == 1
    source.acknowledge(set())
    assert len(http.calls) == 1


def test_first_run_with_no_messages():
    source = TelegramSource("T", None, FakeHttp(ok()))
    with pytest.raises(SourceError) as info:
        source.fetch()
    assert "  (none yet — send your bot a message, then pull again)" in str(info.value)


def test_webhook_conflict_message(monkeypatch):
    def boom(request, timeout=None):
        raise urllib.error.HTTPError(request.full_url, 409, "Conflict", {}, io.BytesIO(b""))
    monkeypatch.setattr(urllib.request, "urlopen", boom)
    with pytest.raises(SourceError) as info:
        TelegramSource("SECRET", 1).fetch()
    assert str(info.value) == "Telegram refused: remove the bot's webhook (deleteWebhook) to use pull"
    assert "SECRET" not in str(info.value)
    assert info.value.__cause__ is None and info.value.__context__ is None


@pytest.mark.parametrize("exc", [
    urllib.error.URLError("https://api.telegram.org/botSECRET/getUpdates failed"),
    urllib.error.URLError("failed https://api.telegram.org/botSECRET/getUpdates"),
    urllib.error.HTTPError("https://api.telegram.org/botSECRET/x", 500, "Err", {}, io.BytesIO(b"")),
    TimeoutError("botSECRET"),
    ConnectionResetError("botSECRET"),
])
def test_token_never_in_errors(monkeypatch, exc):
    def boom(request, timeout=None):
        raise exc
    monkeypatch.setattr(urllib.request, "urlopen", boom)
    source = TelegramSource("SECRET", 1)
    with pytest.raises(SourceError) as info:
        source.fetch()
    assert str(info.value) == f"could not reach Telegram ({type(exc).__name__})"
    assert info.value.__cause__ is None and info.value.__context__ is None
    assert "SECRET" not in str(info.value)


class _Reply:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return self.body


def test_invalid_json_becomes_source_error(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", lambda r, timeout=None: _Reply(b"<html>botSECRET"))
    with pytest.raises(SourceError) as info:
        TelegramSource("SECRET", 1).fetch()
    assert "SECRET" not in str(info.value)
    assert info.value.__cause__ is None and info.value.__context__ is None


def test_ok_false_becomes_source_error(monkeypatch):
    body = b'{"ok": false, "description": "Unauthorized"}'
    monkeypatch.setattr(urllib.request, "urlopen", lambda r, timeout=None: _Reply(body))
    with pytest.raises(SourceError) as info:
        TelegramSource("SECRET", 1).fetch()
    assert str(info.value) == "Telegram refused: Unauthorized"


def test_created_at_from_send_date():
    http = FakeHttp(ok(msg(5, text="x", date=1767225600)))
    item = TelegramSource("T", 123456789, http).fetch().items[0]
    assert item.created_at == "2026-01-01T00:00:00.000000+00:00"
