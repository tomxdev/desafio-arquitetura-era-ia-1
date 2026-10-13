from typing import Protocol


class LLMGateway(Protocol):
    """Pede ao modelo uma capacidade lógica; qual provider e qual modelo atendem é decisão de quem implementa."""

    def complete(self, capability: str, task: str, content: str) -> str: ...
