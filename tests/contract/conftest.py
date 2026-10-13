import os

import httpx
import pytest

BASE_URL = os.getenv("HELPDESK_BASE_URL", "http://localhost:8000")
PROVIDER_URL = os.getenv("PROVIDER_ADMIN_URL", "http://localhost:8090")


@pytest.fixture(scope="session")
def edge():
    # Todas as medições são pela borda (localhost:8000). Timeout acima dos 30 s da borda.
    with httpx.Client(base_url=BASE_URL, timeout=httpx.Timeout(90.0)) as http:
        yield http


@pytest.fixture(scope="session")
def provider():
    with httpx.Client(base_url=PROVIDER_URL, timeout=10.0) as http:
        yield http


@pytest.fixture(autouse=True)
def provider_normal(provider):
    """Cada teste começa e termina com o provider simulado em modo normal."""
    provider.post("/admin/reset").raise_for_status()
    yield
    provider.post("/admin/reset").raise_for_status()


@pytest.fixture
def fail(provider):
    def apply(**mode):
        provider.post("/admin/failures", json=mode).raise_for_status()
    return apply
