"""Grava os goldens da suíte a partir da aplicação no ar (executado uma vez, contra a v1-coupled).

    python tests/characterization/record_golden.py

Usa a mesma borda e as mesmas requisições dos testes. Não deve ser rodado de novo depois da tag
v1-coupled: a suíte existe para comparar as versões seguintes com este registro.
"""

import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent))

from cases import CASES  # noqa: E402
from conftest import BASE_URL, GOLDEN, PROVIDER_URL, TIMEOUT, send, snapshot  # noqa: E402


def main() -> None:
    GOLDEN.mkdir(exist_ok=True)
    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client, httpx.Client(base_url=PROVIDER_URL) as provider:
        for case in CASES:
            provider.post("/admin/reset").raise_for_status()
            data = snapshot(send(client, case))
            (GOLDEN / f"{case.name}.json").write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
            print(f"{case.name}: {data['status']}")


if __name__ == "__main__":
    main()
