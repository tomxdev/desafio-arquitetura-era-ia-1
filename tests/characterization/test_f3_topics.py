"""F3 Relatório de temas: POST /reports/topics.

Na main o relatório é assíncrono (Asynchronous Request-Reply): o pedido responde 202 com Location
e Retry-After; a URL de status responde 303 quando a tarefa termina; o resultado reproduz o relatório
gravado da v1-coupled. Os erros de entrada continuam respondendo 422 no próprio pedido.
"""

import pytest

from cases import by_feature
from conftest import load_golden, send, snapshot, wait_report


@pytest.mark.parametrize("case", by_feature("f3"), ids=lambda c: c.name)
def test_f3_topics(client, case):
    golden = load_golden(case.name)
    if "erro" in case.tags:
        assert snapshot(send(client, case)) == golden
        return

    accepted = send(client, case)
    assert accepted.status_code == 202
    assert accepted.headers["retry-after"]
    result = wait_report(client, accepted.headers["location"])
    assert snapshot(result) == golden
