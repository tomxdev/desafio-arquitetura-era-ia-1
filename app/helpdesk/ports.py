from collections.abc import Iterator
from datetime import date
from typing import Protocol


class CapabilityUnavailable(Exception):
    """A capacidade não pôde ser atendida (falha, timeout, orçamento ou limite), antes ou durante a geração."""

    def __init__(self, capability: str, reason: str) -> None:
        super().__init__(f"{capability}: {reason}")
        self.capability = capability
        self.reason = reason


class LLMGateway(Protocol):
    """Pede ao modelo uma capacidade lógica; qual provider e qual modelo atendem é decisão de quem implementa."""

    def complete(self, capability: str, task: str, content: str) -> str: ...

    def stream(self, capability: str, task: str, content: str) -> Iterator[str]:
        """Trechos do texto à medida que são gerados. Falha antes do 1º trecho: levanta na chamada;
        falha no meio: levanta durante a iteração (sempre CapabilityUnavailable)."""
        ...


class TicketSource(Protocol):
    """Fornece os tickets criados no período (datas inclusivas); de onde eles vêm é decisão de quem implementa."""

    def in_period(self, start: date, end: date) -> list[dict]: ...
