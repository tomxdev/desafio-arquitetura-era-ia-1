"""F2 Sugerir resposta: POST /tickets/reply-suggestion.

Na main a sugestão chega por streaming (SSE): os trechos (`data: {"chunk": ...}`), concatenados,
reproduzem a sugestão gravada da v1-coupled, e o stream termina com `event: end`. Os erros de
entrada continuam respondendo 422 em JSON, antes de o stream começar.
"""

import pytest

from cases import by_feature
from conftest import load_golden, send, snapshot, stream_suggestion


@pytest.mark.parametrize("case", by_feature("f2"), ids=lambda c: c.name)
def test_f2_suggestion(client, case):
    golden = load_golden(case.name)
    if "erro" in case.tags:
        assert snapshot(send(client, case)) == golden
        return

    response, events = stream_suggestion(client, case)
    assert response.status_code == golden["status"]
    assert response.headers["content-type"].startswith("text/event-stream")
    chunks = [data["chunk"] for name, data in events if name == "message"]
    assert "".join(chunks) == golden["body"]["suggestion"]
    assert events[-1] == ("end", {"ticket_id": golden["body"]["ticket_id"]})
