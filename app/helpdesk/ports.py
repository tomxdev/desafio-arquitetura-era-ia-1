from datetime import date
from typing import Protocol


class CapabilityUnavailable(Exception):
    """Nenhum destino conseguiu atender a capacidade (falha, timeout, orçamento ou limite)."""

    def __init__(self, capability: str, reason: str) -> None:
        super().__init__(f"{capability}: {reason}")
        self.capability = capability
        self.reason = reason


class LLMGateway(Protocol):
    """Pede ao modelo uma capacidade lógica; qual provider e qual modelo atendem é decisão de quem implementa."""

    def complete(self, capability: str, task: str, content: str) -> str: ...


class TicketSource(Protocol):
    """Fornece os tickets criados no período (datas inclusivas); de onde eles vêm é decisão de quem implementa."""

    def in_period(self, start: date, end: date) -> list[dict]: ...
