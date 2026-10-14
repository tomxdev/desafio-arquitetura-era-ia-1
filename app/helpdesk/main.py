import os

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse

from . import classification, extraction, suggestion
from .adapters.gateway import GatewayClient
from .ports import CapabilityUnavailable
from .report_jobs import TopicsJobs
from .schemas import Classification, OrderData, PeriodInput, TicketInput, TopicsReport
from .tickets import JsonlTicketSource

# Ponto de composição: o que muda por ambiente vem do ambiente e é injetado nas features.
MAX_OUTPUT_TOKENS = 2000

# Timeout por chamada ao gateway, por capacidade (ADR 0007/0009): abaixo dos 15 s exigidos para as
# features síncronas e dos 30 s da borda; na F2 vale como espera máxima pelo 1º trecho e entre
# trechos; na F3, por lote, garante que uma tarefa travada chegue a `failed` em menos de 60 s.
TIMEOUTS = {
    "helpdesk-classify": 12.0,
    "helpdesk-extract": 12.0,
    "helpdesk-suggest": 12.0,
    "helpdesk-topics": 50.0,
}

gateway = GatewayClient(
    base_url=os.environ["GATEWAY_BASE_URL"],
    api_key=os.environ["GATEWAY_API_KEY"],
    timeouts=TIMEOUTS,
    default_timeout=float(os.environ.get("GATEWAY_TIMEOUT_SECONDS", "12")),
    max_tokens=MAX_OUTPUT_TOKENS,
)
ticket_source = JsonlTicketSource(os.environ.get("TICKETS_FILE", "/data/tickets.jsonl"))
topics_jobs = TopicsJobs(gateway, ticket_source)

app = FastAPI(title="Helpdesk")


@app.exception_handler(CapabilityUnavailable)
def capability_unavailable(request: Request, error: CapabilityUnavailable) -> JSONResponse:
    # Falha explícita e rápida em vez de 500 genérico ou de 504 da borda (tabela de fallback, ADR 0006).
    return JSONResponse(status_code=503, content={
        "detail": f"Capacidade {error.capability} indisponível: {error.reason}"})


@app.get("/health")
def health():
    return {"status": "ok"}


# F1: síncrono, com o resultado completo no corpo.
@app.post("/tickets/classification")
def classify_ticket(ticket: TicketInput) -> Classification:
    return classification.classify(ticket, gateway)


# F2: streaming (SSE). X-Accel-Buffering desliga o buffer da borda (nginx) para esta resposta.
@app.post("/tickets/reply-suggestion")
def suggest_reply(ticket: TicketInput) -> StreamingResponse:
    events = suggestion.suggest(ticket, gateway)
    return StreamingResponse(events, media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# F4: síncrono, com o resultado completo no corpo.
@app.post("/tickets/extraction")
def extract_order_data(ticket: TicketInput) -> OrderData:
    return extraction.extract(ticket, gateway)


# F3: Asynchronous Request-Reply.
@app.post("/reports/topics", status_code=202)
def topics_report(period: PeriodInput, response: Response) -> dict:
    job_id = topics_jobs.submit(period)
    response.headers["Location"] = f"/reports/topics/status/{job_id}"
    response.headers["Retry-After"] = "5"
    return {"job_id": job_id, "state": "pending"}


@app.get("/reports/topics/status/{job_id}", response_model=None)
def topics_report_status(job_id: str) -> dict | RedirectResponse:
    status = topics_jobs.status(job_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Tarefa de relatório não encontrada")
    if status["state"] == "done":
        return RedirectResponse(f"/reports/topics/{job_id}", status_code=303)
    return status


@app.get("/reports/topics/{job_id}")
def topics_report_result(job_id: str) -> TopicsReport:
    result = topics_jobs.result(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Relatório não encontrado ou ainda não concluído")
    return result
