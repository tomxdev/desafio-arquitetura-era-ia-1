import json
import os
import sys
import time
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).parent))

BASE_URL = os.getenv("HELPDESK_BASE_URL", "http://localhost:8000")
PROVIDER_URL = os.getenv("PROVIDER_ADMIN_URL", "http://localhost:8090")
GOLDEN = Path(__file__).parent / "golden"
# Acima dos 30 s da borda: quem corta uma requisição lenta é a borda, não o teste.
TIMEOUT = httpx.Timeout(60.0)


def send(client: httpx.Client, case) -> httpx.Response:
    if case.raw is not None:
        return client.post(case.path, content=case.raw.encode("utf-8"),
                           headers={"Content-Type": "application/json"})
    return client.post(case.path, json=case.body)


def snapshot(response: httpx.Response) -> dict:
    return {
        "status": response.status_code,
        "content_type": response.headers.get("content-type"),
        "body": response.json(),
    }


def load_golden(name: str) -> dict:
    return json.loads((GOLDEN / f"{name}.json").read_text(encoding="utf-8"))


# Na main, F2 e F3 mudaram de modo de execução (requisito 6). Os goldens continuam os da v1: o
# conteúdo entregue tem de ser o mesmo; muda só a forma de consumir (SSE e polling).

def sse_events(response: httpx.Response) -> list[tuple[str, dict]]:
    """[(evento, dados)] de uma resposta text/event-stream (evento padrão: "message")."""
    events, name = [], "message"
    for line in response.iter_lines():
        if line.startswith("event: "):
            name = line[len("event: "):]
        elif line.startswith("data: "):
            events.append((name, json.loads(line[len("data: "):])))
            name = "message"
    return events


def stream_suggestion(client: httpx.Client, case) -> tuple[httpx.Response, list[tuple[str, dict]]]:
    with client.stream("POST", case.path, json=case.body) as response:
        return response, sse_events(response)


def wait_report(client: httpx.Client, location: str, timeout: float = 120.0) -> httpx.Response:
    """Consulta a URL de status até o 303 e devolve a resposta do resultado."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status = client.get(location)
        if status.status_code == 303:
            return client.get(status.headers["location"])
        assert status.status_code == 200 and status.json()["state"] in ("pending", "running"), status.text
        time.sleep(1)
    raise AssertionError(f"relatório não ficou pronto em {timeout} s")


@pytest.fixture(scope="session")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as http:
        yield http


@pytest.fixture(scope="session")
def provider():
    with httpx.Client(base_url=PROVIDER_URL, timeout=10.0) as http:
        yield http


@pytest.fixture(autouse=True)
def provider_normal(provider):
    """Cada teste começa com o provider simulado em modo normal."""
    provider.post("/admin/reset").raise_for_status()
