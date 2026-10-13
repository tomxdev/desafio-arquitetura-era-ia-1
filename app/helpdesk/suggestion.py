import json
from collections.abc import Iterator

from .ports import CapabilityUnavailable, LLMGateway
from .schemas import TicketInput

CAPABILITY = "helpdesk-suggest"
INTERRUPTED = "A geração foi interrompida"


def suggest(ticket: TicketInput, gateway: LLMGateway) -> Iterator[str]:
    """Eventos SSE da sugestão: os trechos à medida que chegam, e um `end` ou um `error` no fim.

    A requisição ao gateway sai já nesta chamada: se nenhum destino responder antes do 1º trecho,
    `CapabilityUnavailable` sobe daqui (a rota ainda pode responder 503). Depois que o 1º trecho foi
    enviado, o status 200 já saiu; uma falha vira o evento `error` e o stream termina.
    """
    chunks = gateway.stream(CAPABILITY, "suggest", ticket.text)
    return _events(ticket.ticket_id, chunks)


def _events(ticket_id: str, chunks: Iterator[str]) -> Iterator[str]:
    try:
        for chunk in chunks:
            yield _event({"chunk": chunk})
    except CapabilityUnavailable:
        yield _event({"ticket_id": ticket_id, "message": INTERRUPTED}, name="error")
        return
    yield _event({"ticket_id": ticket_id}, name="end")


def _event(data: dict, name: str | None = None) -> str:
    prefix = f"event: {name}\n" if name else ""
    return f"{prefix}data: {json.dumps(data, ensure_ascii=False)}\n\n"
