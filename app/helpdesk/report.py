import json
from collections.abc import Callable

from fastapi import HTTPException

from .ports import LLMGateway, TicketSource
from .schemas import PeriodInput, Topic, TopicsReport

CAPABILITY = "helpdesk-topics"
TICKETS_PER_CALL = 150


def validate(period: PeriodInput) -> None:
    if period.start > period.end:
        raise HTTPException(status_code=422, detail="A data inicial é posterior à data final")


def topics(period: PeriodInput, gateway: LLMGateway, tickets: TicketSource,
           on_progress: Callable[[int, int], None] | None = None) -> TopicsReport:
    validate(period)
    selected = tickets.in_period(period.start, period.end)
    if on_progress:
        on_progress(0, len(selected))

    # O mês inteiro não cabe numa chamada: processa em lotes, um depois do outro.
    totals: dict[str, dict] = {}
    for first in range(0, len(selected), TICKETS_PER_CALL):
        batch = selected[first:first + TICKETS_PER_CALL]
        content = "\n".join(f"[{t['id']}] {t['text']}" for t in batch)
        answer = json.loads(gateway.complete(CAPABILITY, "topics", content))
        for item in answer["topics"]:
            current = totals.setdefault(item["topic"], {"count": 0, "examples": []})
            current["count"] += item["count"]
            current["examples"] = (current["examples"] + item["examples"])[:3]
        if on_progress:
            on_progress(first + len(batch), len(selected))

    items = [Topic(topic=name, **data) for name, data in totals.items()]
    items.sort(key=lambda t: (-t.count, t.topic))
    return TopicsReport(start=period.start, end=period.end, total_tickets=len(selected), topics=items)
