from datetime import date
from typing import Protocol


class LLMGateway(Protocol):
    """Pede ao modelo uma capacidade lógica; qual provider e qual modelo atendem é decisão de quem implementa."""

    def complete(self, capability: str, task: str, content: str) -> str: ...


class TicketSource(Protocol):
    """Fornece os tickets criados no período (datas inclusivas); de onde eles vêm é decisão de quem implementa."""

    def in_period(self, start: date, end: date) -> list[dict]: ...
