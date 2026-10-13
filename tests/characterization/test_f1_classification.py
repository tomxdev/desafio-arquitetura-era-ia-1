"""F1 Classificar ticket: POST /tickets/classification, resposta síncrona em JSON."""

import pytest

from cases import by_feature
from conftest import load_golden, send, snapshot


@pytest.mark.parametrize("case", by_feature("f1"), ids=lambda c: c.name)
def test_f1_classification(client, case):
    assert snapshot(send(client, case)) == load_golden(case.name)
