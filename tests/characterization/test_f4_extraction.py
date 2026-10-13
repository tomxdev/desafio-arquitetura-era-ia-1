"""F4 Extrair dados do pedido: POST /tickets/extraction, resposta síncrona em JSON."""

import pytest

from cases import by_feature
from conftest import load_golden, send, snapshot


@pytest.mark.parametrize("case", by_feature("f4"), ids=lambda c: c.name)
def test_f4_extraction(client, case):
    assert snapshot(send(client, case)) == load_golden(case.name)
