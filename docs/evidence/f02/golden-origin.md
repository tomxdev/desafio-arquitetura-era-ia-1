# Origem dos goldens da suíte de caracterização (F02)

- Gravados em 2026-10-13 por `python tests/characterization/record_golden.py` contra a aplicação **recebida** (`app/` idêntico a `upstream/main`, `a1aedd76`), no compose, pela borda `localhost:8000`, com `POST /admin/reset` antes de cada caso (provider simulado em modo normal).
- Cada golden fixa `status`, `content_type` e o **corpo inteiro** da resposta (`tests/characterization/golden/<caso>.json`).
- Escopo: comportamento em modo normal + erros de entrada (17 casos: 10 de sucesso, 7 de erro; pelo menos um de erro por feature). Falhas do provider **não** são fixadas aqui: esse comportamento muda de propósito a partir da v2 (fallback), e a suíte precisa ser idêntica entre `v1-coupled` e `v2-decoupled`.
- F3 usa um dia (`2026-08-01`: 137 tickets, um lote, ~10 s): o mês inteiro termina em 504 da borda na v1 (diagnóstico, dor 1).
- Os erros 422 vêm do FastAPI/pydantic da imagem (`fastapi 0.115.6`, `pydantic 2.14.1`, `pydantic_core 2.50.1`, `starlette 0.41.3`). O corpo inclui `msg` e `ctx` do pydantic: uma versão diferente na v2 pode mudar o texto. Por isso, a F05 fixa essas versões no `app/requirements.txt`.
- Determinismo: duas execuções seguidas, 17/17 em ambas (`docs/evidence/f02/pytest-v1.txt`).
