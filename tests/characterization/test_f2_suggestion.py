"""F2 Sugerir resposta: POST /tickets/reply-suggestion, resposta síncrona em JSON com o texto inteiro."""

import pytest

from cases import by_feature
from conftest import load_golden, send, snapshot


@pytest.mark.parametrize("case", by_feature("f2"), ids=lambda c: c.name)
def test_f2_suggestion(client, case):
    assert snapshot(send(client, case)) == load_golden(case.name)
