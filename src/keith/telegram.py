import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.client import HTTPException
from typing import Callable

from keith.importers import FetchResult, RawItem, SourceError


WEBHOOK_MESSAGE = "Telegram refused: remove the bot's webhook (deleteWebhook) to use pull"


def _unreachable(exc: Exception) -> SourceError:
    # Only the exception's class name is used: urllib messages can contain the URL (and token).
    return SourceError(f"could not reach Telegram ({type(exc).__name__})")


def _default_http(token: str) -> Callable[[str, dict], dict]:
    def http(method: str, params: dict) -> dict:
        request = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/{method}",
            data=json.dumps(params).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                reply = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 409:
                raise SourceError(WEBHOOK_MESSAGE) from None
            raise _unreachable(exc) from None
        except (OSError, HTTPException) as exc:
            raise _unreachable(exc) from None
        except ValueError:
            raise SourceError("Telegram sent an unreadable reply") from None
        if not isinstance(reply, dict):
            raise SourceError("Telegram sent an unreadable reply")
        if not reply.get("ok"):
            raise SourceError(f"Telegram refused: {reply.get('description', 'unknown error')}")
        return reply
    return http


class TelegramSource:
    name = "Telegram"

    def __init__(self, token: str, user_id: int | None,
                 http: Callable[[str, dict], dict] | None = None):
        self.user_id = user_id
        self.http = http or _default_http(token)
        self._update_ids: dict[str, int] = {}
        self._highest: int | None = None

    def fetch(self) -> FetchResult:
        reply = self.http("getUpdates", {"timeout": 0, "limit": 100})
        updates = reply.get("result", [])
        self._update_ids = {}
        self._highest = max((u["update_id"] for u in updates), default=None)

        if self.user_id is None:
            self._highest = None
            raise SourceError(self._sender_listing(updates))

        result = FetchResult([])
        for update in updates:
            message = update.get("message")
            if message is None:
                continue
            sender = message.get("from", {}).get("id")
            if sender != self.user_id:
                result.skipped["other senders"] = result.skipped.get("other senders", 0) + 1
                continue
            text = message.get("text") or message.get("caption")
            if not text:
                result.skipped["no text"] = result.skipped.get("no text", 0) + 1
                continue
            key = f"{message['chat']['id']}:{message['message_id']}"
            self._update_ids[key] = update["update_id"]
            created_at = datetime.fromtimestamp(message["date"], timezone.utc).isoformat(
                timespec="microseconds")
            result.items.append(RawItem(self.name, key, text, created_at))
        return result

    @staticmethod
    def _sender_listing(updates: list[dict]) -> str:
        senders: dict[int, list] = {}
        for update in updates:
            message = update.get("message")
            if not message or "id" not in message.get("from", {}):
                continue
            sender = message["from"]
            entry = senders.setdefault(sender["id"], [sender.get("first_name", ""), 0])
            entry[1] += 1
        lines = ["set KEITH_TELEGRAM_USER to import. Senders waiting:"]
        if not senders:
            lines.append("  (none yet — send your bot a message, then pull again)")
        for sender_id, (first_name, count) in senders.items():
            noun = "message" if count == 1 else "messages"
            lines.append(f"  {sender_id}  {first_name} ({count} {noun})")
        return "\n".join(lines)

    def acknowledge(self, failed_keys: set[str]) -> None:
        if self.user_id is None or self._highest is None:
            return
        failed = [self._update_ids[k] for k in failed_keys if k in self._update_ids]
        offset = min(failed) if failed else self._highest + 1
        self.http("getUpdates", {"offset": offset, "timeout": 0, "limit": 1})
