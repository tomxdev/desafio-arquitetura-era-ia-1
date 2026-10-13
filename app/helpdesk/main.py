import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from . import classification, extraction, report, suggestion
from .adapters.gateway import GatewayClient
from .ports import CapabilityUnavailable
from .schemas import (Classification, OrderData, PeriodInput, ReplySuggestion, TicketInput,
                      TopicsReport)
from .tickets import JsonlTicketSource

# Ponto de composição: o que muda por ambiente vem do ambiente e é injetado nas features.
MAX_OUTPUT_TOKENS = 2000

gateway = GatewayClient(
    base_url=os.environ["GATEWAY_BASE_URL"],
    api_key=os.environ["GATEWAY_API_KEY"],
    timeout=float(os.environ.get("GATEWAY_TIMEOUT_SECONDS", "60")),
    max_tokens=MAX_OUTPUT_TOKENS,
)
ticket_source = JsonlTicketSource(os.environ.get("TICKETS_FILE", "/data/tickets.jsonl"))

app = FastAPI(title="Helpdesk")


@app.exception_handler(CapabilityUnavailable)
def capability_unavailable(request: Request, error: CapabilityUnavailable) -> JSONResponse:
    # Falha explícita e rápida em vez de 500 genérico ou de 504 da borda (tabela de fallback, ADR 0006).
    return JSONResponse(status_code=503, content={
        "detail": f"Capacidade {error.capability} indisponível: {error.reason}"})


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/tickets/classification")
def classify_ticket(ticket: TicketInput) -> Classification:
    return classification.classify(ticket, gateway)


@app.post("/tickets/reply-suggestion")
def suggest_reply(ticket: TicketInput) -> ReplySuggestion:
    return suggestion.suggest(ticket, gateway)


@app.post("/tickets/extraction")
def extract_order_data(ticket: TicketInput) -> OrderData:
    return extraction.extract(ticket, gateway)


@app.post("/reports/topics")
def topics_report(period: PeriodInput) -> TopicsReport:
    return report.topics(period, gateway, ticket_source)
