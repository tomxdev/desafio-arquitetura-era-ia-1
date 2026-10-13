import json
import os
import sys
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
