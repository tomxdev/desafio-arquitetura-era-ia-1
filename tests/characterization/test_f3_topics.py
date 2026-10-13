"""F3 Relatório de temas: POST /reports/topics, resposta síncrona em JSON com o relatório inteiro.

Na v1, o mês inteiro termina em 504 da borda (diagnóstico, dor 1); a suíte fixa um período de um dia.
"""

import pytest

from cases import by_feature
from conftest import load_golden, send, snapshot


@pytest.mark.parametrize("case", by_feature("f3"), ids=lambda c: c.name)
def test_f3_topics(client, case):
    assert snapshot(send(client, case)) == load_golden(case.name)
