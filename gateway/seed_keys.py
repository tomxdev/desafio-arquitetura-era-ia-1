"""Cria as chaves virtuais do gateway de forma idempotente (roda dentro do container do gateway).

Espera o proxy responder, e para cada chave declarada em KEYS: se ela já existe (/key/info), não
faz nada; senão, revoga as chaves com o mesmo alias (rotação: o valor no .env mudou) e cria a nova
com /key/generate usando o valor fixo vindo do ambiente. Assim a aplicação recebe a sua chave por
variável de ambiente, sem passo manual e sem conhecer a master key.

Os limites (orçamento, rpm) valem na criação: para mudá-los numa chave existente, recrie o volume
do banco (`docker compose down -v`) ou troque o valor da chave. Chaves (ADR 0004):
- helpdesk-app: a do serviço app; teto mensal de gasto (ADR 0005) e limite de requisições folgado.
- demo-budget e demo-rpm: só para o roteiro de governança do README; não são usadas pelo app.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:4000"
MASTER = os.environ["LITELLM_MASTER_KEY"]
CAPABILITIES = ["helpdesk-classify", "helpdesk-suggest", "helpdesk-topics", "helpdesk-extract"]

KEYS = [
    {"key": os.environ["HELPDESK_GATEWAY_KEY"], "key_alias": "helpdesk-app", "models": CAPABILITIES,
     "max_budget": 50.0, "budget_duration": "30d", "rpm_limit": 600},
    # Orçamento de US$ 0,0001: a 1ª classificação (~US$ 0,00016) passa e estoura; a 2ª é recusada.
    {"key": os.environ["GATEWAY_DEMO_BUDGET_KEY"], "key_alias": "demo-budget", "models": ["helpdesk-classify"],
     "max_budget": 0.0001},
    # 2 requisições por minuto: a 3ª no mesmo minuto é recusada.
    {"key": os.environ["GATEWAY_DEMO_RPM_KEY"], "key_alias": "demo-rpm", "models": ["helpdesk-classify"],
     "rpm_limit": 2},
]


def request(method: str, path: str, body: dict | None = None) -> tuple[int, dict | str]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{BASE}{path}", data=data, method=method, headers={
        "Authorization": f"Bearer {MASTER}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            raw = response.read().decode()
            status = response.status
    except urllib.error.HTTPError as error:
        raw, status = error.read().decode(), error.code
    try:
        return status, json.loads(raw)
    except json.JSONDecodeError:
        return status, raw


def wait_ready(timeout: float = 180) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            status, body = request("GET", "/health/readiness")
            if status == 200 and isinstance(body, dict) and body.get("db") == "connected":
                return
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            pass
        time.sleep(2)
    sys.exit("gateway não ficou pronto a tempo")


def main() -> None:
    wait_ready()
    for spec in KEYS:
        status, _ = request("GET", f"/key/info?key={spec['key']}")
        if status == 200:
            print(f"chave {spec['key_alias']}: já existe", flush=True)
            continue
        status, body = request("POST", "/key/delete", {"key_aliases": [spec["key_alias"]]})
        if status == 200:
            print(f"chave {spec['key_alias']}: valor anterior revogado", flush=True)
        status, body = request("POST", "/key/generate", spec)
        if status != 200 or body.get("key") != spec["key"]:
            sys.exit(f"falha ao criar a chave {spec['key_alias']}: {status} {body}")
        print(f"chave {spec['key_alias']}: criada", flush=True)


if __name__ == "__main__":
    main()
