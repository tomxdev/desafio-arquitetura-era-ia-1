import json
from datetime import date, datetime

from .ports import TicketSource


class JsonlTicketSource(TicketSource):
    """TicketSource sobre um arquivo JSON Lines (um ticket por linha, com `created_at` ISO 8601)."""

    def __init__(self, path: str) -> None:
        self._path = path

    def in_period(self, start: date, end: date) -> list[dict]:
        selected = []
        with open(self._path, encoding="utf-8") as file:
            for line in file:
                ticket = json.loads(line)
                day = datetime.fromisoformat(ticket["created_at"]).date()
                if start <= day <= end:
                    selected.append(ticket)
        return selected
