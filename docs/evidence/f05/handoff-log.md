# F05: log do handoff ao agente de refatoração

Branch `feature/05-gateway-v2`. Um alvo por vez, na ordem do plano (`docs/refactoring-plan.md`, seção 6). Para cada alvo, os quatro juízes rodaram **antes** do commit:

| Juiz | Comando |
|---|---|
| J1 Comportamento | `docker compose up -d --build --wait app && .venv/Scripts/python -m pytest tests/characterization -q` (alvo 5: `docker compose up -d --build --wait`) |
| J2 Suíte intocada | `git diff --exit-code v1-coupled -- tests/characterization/` |
| J3 Estrutura | `.venv/Scripts/python metrics/coupling.py app/helpdesk --name wip --out-dir /tmp/f05-wip`; zona de dor = A<0.5 e I<0.5 e D>=0.5 |
| J4 Restrições | `grep -rE "gpt-fake\|claude-fake" app/`; `grep -rE "FAKE_OPENAI_KEY\|FAKE_ANTHROPIC_KEY\|sk-fake-openai\|sk-ant-fake" app/`; `grep -rnE "adapters\|tickets import\|import tickets" app/helpdesk --include=*.py \| grep -v main.py`; `docker compose exec app env \| grep -E "FAKE_\|sk-fake\|sk-ant"` (obrigatório só a partir do alvo 5) |

Ponto de partida (branch no commit `91c83f5`):

```csv
component,ca,ce,i,a,d
classification,1,2,0.67,0.00,0.33
config,5,0,0.00,0.00,1.00
extraction,1,3,0.75,0.00,0.25
llm,4,1,0.20,0.00,0.80
main,0,6,1.00,0.00,0.00
ports,1,0,0.00,1.00,0.00
report,1,4,0.80,0.00,0.20
schemas,5,0,0.00,0.00,1.00
suggestion,1,3,0.75,0.00,0.25
tickets,1,1,0.50,0.00,0.50
```

## Alvo 1: suggestion

**O que mudou:** `suggestion.suggest(ticket, gateway: LLMGateway)` com `CAPABILITY = "helpdesk-suggest"`; deixou de importar `config`/`llm`. `classification.CAPABILITY` renomeada de `"classification"` para `"helpdesk-classify"`. `ProviderGateway` mapeia `helpdesk-classify` → `call_openai(CLASSIFICATION_MODEL)` e `helpdesk-suggest` → `call_anthropic(SUGGESTION_MODEL)` (as chamadas da v1). `main` injeta o gateway na rota.

**J1:** `17 passed` (~35 s). **J2:** diff vazio (exit 0). **J3:** zona de dor = `config`, `llm`, `schemas` (permitidos enquanto `config`/`llm` existirem); features dependem só de `ports` e `schemas`.

```csv
component,ca,ce,i,a,d
classification,1,2,0.67,0.00,0.33
config,4,0,0.00,0.00,1.00
extraction,1,3,0.75,0.00,0.25
llm,3,1,0.25,0.00,0.75
main,0,6,1.00,0.00,0.00
ports,2,0,0.00,1.00,0.00
report,1,4,0.80,0.00,0.20
schemas,5,0,0.00,0.00,1.00
suggestion,1,2,0.67,0.00,0.33
tickets,1,1,0.50,0.00,0.50
```

**J4:** informativo neste alvo: nomes físicos e chaves ainda em `config.py`; nenhum import de `adapters`/`tickets` fora do `main`; `FAKE_*` ainda no ambiente do app (env_file).

**Rejeições/iterações:** nenhuma rejeição de código. Na primeira execução, o passo de leitura do CSV do meu script de juízes falhou por caminho `/tmp` (Python do Windows não resolve o `/tmp` do Git Bash); corrigi o script (via `cygpath`), não a métrica, e reavaliei o mesmo CSV: `['config', 'llm', 'schemas']`.

## Alvo 2: extraction

**O que mudou:** `extraction.extract(ticket, gateway)` com `CAPABILITY = "helpdesk-extract"` e `json.loads` local; deixou de importar `config`/`llm`. `ProviderGateway` mapeia `helpdesk-extract` → `call_openai(EXTRACTION_MODEL)`. O 502 de formato inválido ficou idêntico.

**J1:** `17 passed` (~35 s). **J2:** diff vazio (exit 0). **J3:** zona de dor = `config`, `llm`, `schemas`; features dependem só de `ports` e `schemas`.

```csv
component,ca,ce,i,a,d
classification,1,2,0.67,0.00,0.33
config,3,0,0.00,0.00,1.00
extraction,1,2,0.67,0.00,0.33
llm,2,1,0.33,0.00,0.67
main,0,6,1.00,0.00,0.00
ports,3,0,0.00,1.00,0.00
report,1,4,0.80,0.00,0.20
schemas,5,0,0.00,0.00,1.00
suggestion,1,2,0.67,0.00,0.33
tickets,1,1,0.50,0.00,0.50
```

**J4:** informativo: igual ao alvo 1.

**Rejeições/iterações:** nenhuma.

## Alvo 3: report + tickets

**O que mudou:** `ports.TicketSource(Protocol)` com `in_period(start, end) -> list[dict]`. `tickets.JsonlTicketSource(TicketSource)` recebe o caminho no construtor (mesma leitura linha a linha). `report.topics(period, gateway, tickets)` com `CAPABILITY = "helpdesk-topics"`, `TICKETS_PER_CALL = 150` local e `json.loads` local; mesma checagem 422, mesmos lotes sequenciais, agregação e ordenação. `ProviderGateway` mapeia `helpdesk-topics` → `call_anthropic(REPORT_MODEL)`. `main` monta `JsonlTicketSource(config.TICKETS_FILE)` (provisório até o alvo 4).

**J1:** `17 passed` (~35 s). **J2:** diff vazio (exit 0). **J3:** zona de dor = `config`, `schemas` (`llm` saiu: I 0.50); features dependem só de `ports` e `schemas`.

```csv
component,ca,ce,i,a,d
classification,1,2,0.67,0.00,0.33
config,2,0,0.00,0.00,1.00
extraction,1,2,0.67,0.00,0.33
llm,1,1,0.50,0.00,0.50
main,0,8,1.00,0.00,0.00
ports,5,0,0.00,1.00,0.00
report,1,2,0.67,0.00,0.33
schemas,5,0,0.00,0.00,1.00
suggestion,1,2,0.67,0.00,0.33
tickets,1,1,0.50,0.00,0.50
```

**J4:** informativo: igual ao alvo 1.

**Rejeições/iterações:** nenhuma.

## Alvo 4: adapters.gateway

**O que mudou:** `app/helpdesk/adapters/__init__.py` (vazio) e `adapters/gateway.py` com `GatewayClient(LLMGateway)`: `OpenAI(base_url, api_key, timeout, max_retries=0)`, `chat.completions.create(model=capability, max_tokens=self._max_tokens, messages=[{"role": "user", "content": f"TASK: {task}\n{content}"}])`, devolve `choices[0].message.content`. `main.py` lê `GATEWAY_BASE_URL`, `GATEWAY_API_KEY`, `GATEWAY_TIMEOUT_SECONDS` (padrão `60`) e `TICKETS_FILE` (padrão `/data/tickets.jsonl`), monta `GatewayClient(max_tokens=2000)` e `JsonlTicketSource` e injeta; não importa mais `config` nem `llm`. `compose.yaml` (serviço app) ganhou o bloco `environment` com `GATEWAY_BASE_URL`/`GATEWAY_API_KEY` **neste alvo** (o `env_file` só saiu no alvo 5), porque sem essas variáveis o app não sobe. Conferido no log do gateway: as chamadas do app chegam como `POST /chat/completions` com 200.

**J1:** `17 passed` (~35 s). **J2:** diff vazio (exit 0). **J3:** zona de dor = `config`, `schemas` (`config` só é importado por `llm`, que ninguém mais importa: Ca 0); features dependem só de `ports` e `schemas`.

```csv
component,ca,ce,i,a,d
adapters.gateway,1,1,0.50,0.00,0.50
classification,1,2,0.67,0.00,0.33
config,1,0,0.00,0.00,1.00
extraction,1,2,0.67,0.00,0.33
llm,0,1,1.00,0.00,0.00
main,0,7,1.00,0.00,0.00
ports,6,0,0.00,1.00,0.00
report,1,2,0.67,0.00,0.33
schemas,5,0,0.00,0.00,1.00
suggestion,1,2,0.67,0.00,0.33
tickets,1,1,0.50,0.00,0.50
```

**J4:** informativo: `config.py` ainda presente (nomes/chaves); `FAKE_*` ainda no ambiente do app.

**Rejeições/iterações:** nenhuma.

## Alvo 5: dissolver config e llm

**O que mudou:** `config.py` e `llm.py` apagados. `app/requirements.txt`: sem `anthropic`; `fastapi==0.115.6`, `uvicorn==0.34.0`, `openai==3.19.0`, `pydantic==2.14.1`, `pydantic_core==2.50.1` (as versões resolvidas pela imagem construída com o requirements da v1, conferidas com `pip freeze` no container antes do rebuild deste alvo). `compose.yaml`, serviço app: removido `env_file: .env`; demais serviços intactos.

**J1:** `17 passed` (~35 s). **J2:** diff vazio (exit 0). **J3:** zona de dor = `schemas` (exceção estável por natureza, ADR 0008); features dependem só de `ports` e `schemas`.

```csv
component,ca,ce,i,a,d
adapters.gateway,1,1,0.50,0.00,0.50
classification,1,2,0.67,0.00,0.33
extraction,1,2,0.67,0.00,0.33
main,0,7,1.00,0.00,0.00
ports,6,0,0.00,1.00,0.00
report,1,2,0.67,0.00,0.33
schemas,5,0,0.00,0.00,1.00
suggestion,1,2,0.67,0.00,0.33
tickets,1,1,0.50,0.00,0.50
```

**J4:** obrigatório e **verde**: os quatro greps vazios. Ambiente do app só com `GATEWAY_BASE_URL` e `GATEWAY_API_KEY` do projeto; `pip freeze` no app sem `anthropic`.

**Rejeições/iterações:** nenhuma.

## Resultado final

- Critério de pronto (seção 3 do plano): suíte 17 passed e intocada; só `schemas` na zona de dor; o código que chama o modelo está só em `adapters.gateway`, importado só por `main`; nenhum nome físico nem chave de provider em `app/` nem no ambiente do serviço app.
- Desvio registrado: o bloco `environment` do serviço app entrou no alvo 4 (e não no 5), porque o `GatewayClient` montado em `main` exige `GATEWAY_BASE_URL`/`GATEWAY_API_KEY` para o app subir; a remoção do `env_file` ficou no alvo 5, como pedido.
