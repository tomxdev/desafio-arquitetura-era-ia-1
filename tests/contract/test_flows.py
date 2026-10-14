"""Contratos da main (requisito 6), medidos pela borda (localhost:8000).

F1 e F4 síncronos; F2 em streaming SSE; F3 em Asynchronous Request-Reply. Inclui os cenários de
falha dos critérios de aceite. O teste do mês inteiro da F3 leva ~6 min e só roda com RUN_SLOW=1.
"""

import json
import os
import time

import pytest

TICKET = {"ticket_id": "TK-00042", "text": "Meu pedido #481516 não chegou e já passou do prazo, urgente"}
MONTH = {"start": "2026-08-01", "end": "2026-08-31"}
DAY = {"start": "2026-08-01", "end": "2026-08-01"}


def is_edge_504(response) -> bool:
    return response.status_code == 504 and "nginx" in response.text


def timed_post(edge, path, body):
    started = time.perf_counter()
    response = edge.post(path, json=body)
    return response, time.perf_counter() - started


def read_sse(edge, body):
    """(response, [(t_desde_o_pedido, evento, dados)], t_total)."""
    started = time.perf_counter()
    events, name = [], "message"
    with edge.stream("POST", "/tickets/reply-suggestion", json=body) as response:
        for line in response.iter_lines():
            if line.startswith("event: "):
                name = line[len("event: "):]
            elif line.startswith("data: "):
                events.append((time.perf_counter() - started, name, json.loads(line[len("data: "):])))
                name = "message"
    return response, events, time.perf_counter() - started


def poll(edge, location, timeout):
    """Consulta a URL de status até sair de pending/running; devolve (resposta, segundos)."""
    started = time.perf_counter()
    while time.perf_counter() - started < timeout:
        status = edge.get(location)
        assert not is_edge_504(status)
        if status.status_code != 200 or status.json()["state"] not in ("pending", "running"):
            return status, time.perf_counter() - started
        time.sleep(1)
    raise AssertionError(f"tarefa ainda em andamento depois de {timeout} s")


# F1 ------------------------------------------------------------------------------------------

def test_f1_result_within_3s(edge):
    response, elapsed = timed_post(edge, "/tickets/classification", TICKET)
    assert response.status_code == 200
    assert response.json() == {"ticket_id": "TK-00042", "category": "delivery", "priority": "high"}
    assert elapsed <= 3.0, elapsed


def test_f1_primary_provider_timeout_answers_within_15s(edge, fail):
    fail(provider="openai", mode="timeout")
    response, elapsed = timed_post(edge, "/tickets/classification", TICKET)
    assert not is_edge_504(response)
    assert response.status_code in (200, 503)
    assert elapsed <= 15.0, elapsed


# F2 ------------------------------------------------------------------------------------------

def test_f2_streams_first_chunk_within_1_5s(edge):
    response, events, total = read_sse(edge, TICKET)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    first_at = events[0][0]
    assert events[0][1] == "message" and events[0][2]["chunk"]
    assert first_at <= 1.5, first_at
    assert first_at < total / 2, (first_at, total)
    assert events[-1][1:] == ("end", {"ticket_id": "TK-00042"})
    assert len([e for e in events if e[1] == "message"]) > 10  # chega aos poucos, não em bloco


def test_f2_midstream_failure_arrives_as_error_event(edge, fail):
    fail(provider="anthropic", model="claude-fake-large", mode="midstream_error")
    response, events, _ = read_sse(edge, TICKET)
    assert response.status_code == 200  # o status já tinha sido enviado
    assert any(name == "message" for _, name, _ in events)  # parte do texto chegou
    assert events[-1][1:] == ("error", {"ticket_id": "TK-00042", "message": "A geração foi interrompida"})


# F3 ------------------------------------------------------------------------------------------

def test_f3_month_request_accepted_within_1s(edge):
    # A tarefa do mês segue rodando (~5 min) depois do teste; os roteiros de scripts/verify começam
    # com quiesce (reinicia o app) para que ela não entre no /admin/calls deles.
    response, elapsed = timed_post(edge, "/reports/topics", MONTH)
    assert response.status_code == 202
    assert response.headers["location"].startswith("/reports/topics/status/")
    assert int(response.headers["retry-after"]) > 0
    assert elapsed <= 1.0, elapsed
    status = edge.get(response.headers["location"])
    assert status.status_code == 200 and status.json()["state"] in ("pending", "running")


def test_f3_both_providers_down_fails_within_60s_with_reason(edge, fail):
    fail(provider="openai", mode="error_500")
    fail(provider="anthropic", mode="error_500")
    accepted, _ = timed_post(edge, "/reports/topics", MONTH)
    assert accepted.status_code == 202
    status, elapsed = poll(edge, accepted.headers["location"], timeout=60)
    assert status.status_code == 200
    assert status.json()["state"] == "failed"
    assert status.json()["reason"]
    assert elapsed <= 60, elapsed


def test_f3_unknown_job_is_404(edge):
    assert edge.get("/reports/topics/status/nao-existe").status_code == 404
    assert edge.get("/reports/topics/nao-existe").status_code == 404


@pytest.mark.skipif(os.getenv("RUN_SLOW") != "1", reason="mês inteiro: ~6 min (RUN_SLOW=1)")
def test_f3_month_report_covers_5000_tickets(edge, provider):
    accepted, _ = timed_post(edge, "/reports/topics", MONTH)
    status, _ = poll(edge, accepted.headers["location"], timeout=900)
    assert status.status_code == 303
    result = edge.get(status.headers["location"])
    assert result.status_code == 200 and result.json()["total_tickets"] == 5000
    # 34 lotes de 150; ">=" porque uma tarefa do mês de outro teste pode ainda estar rodando em paralelo.
    calls = provider.get("/admin/calls", params={"last": 500}).json()
    assert len([c for c in calls if c["task"] == "topics" and c["status"] == 200]) >= 34


# F4 ------------------------------------------------------------------------------------------

def test_f4_without_large_models_fails_explicitly(edge, fail):
    fail(provider="openai", model="gpt-fake-large", mode="error_500")
    fail(provider="anthropic", model="claude-fake-large", mode="error_500")
    response, elapsed = timed_post(edge, "/tickets/extraction", TICKET)
    assert response.status_code == 503
    assert response.json()["detail"].startswith("Capacidade helpdesk-extract indisponível")
    assert elapsed <= 15.0, elapsed
