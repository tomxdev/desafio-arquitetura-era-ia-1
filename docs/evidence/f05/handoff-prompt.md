# F05: prompt entregue ao agente de refatoração

- Agente: subagente Claude Code (modelo Claude Opus 5.5), tipo `general-purpose`, sem isolamento (mesmo clone e mesma branch `feature/05-gateway-v2`), com o compose no ar.
- Entregue em 2026-10-13, depois do commit `91c83f5` (infraestrutura do gateway, verificada antes do handoff).
- Abaixo, o texto literal.

---

Você é o agente de refatoração da fase F05 de um desafio de arquitetura. Trabalhe SOMENTE no repositório local C:\dev\desafio-arquitetura-era-ia-1 (no Git Bash: /c/dev/desafio-arquitetura-era-ia-1), na branch já criada `feature/05-gateway-v2`. NÃO faça push, NÃO abra PR, NÃO crie tags, NÃO troque de branch. Ambiente: Windows + Git Bash; o diretório de trabalho do shell é resetado a cada comando, então comece cada comando com `cd /c/dev/desafio-arquitetura-era-ia-1 &&`. O Python do venv é `.venv/Scripts/python`. O Docker compose do projeto já está no ar (provider-fake, edge, app, gateway LiteLLM em :4000, gateway-db).

## Contexto
Aplicação FastAPI (Python 3.12) em `app/helpdesk/`. Leia primeiro: `docs/refactoring-plan.md` (especialmente "Revisão 1", "Alvos revisados para a v2-decoupled" e "Handoff"), e todo `app/helpdesk/*.py`. O piloto já foi feito: `ports.py` tem `LLMGateway(Protocol)` com `complete(capability, task, content) -> str`; `classification.py` recebe o gateway; `llm.py` tem `ProviderGateway` provisório (chama os SDKs direto); `main.py` monta e injeta.
O gateway LiteLLM já está configurado em `gateway/config.yaml` com as capacidades lógicas `helpdesk-classify`, `helpdesk-suggest`, `helpdesk-topics`, `helpdesk-extract` (API compatível com OpenAI em `http://gateway:4000` dentro do compose; `/v1/chat/completions`, `model` = nome lógico). A chave do app é a variável `HELPDESK_GATEWAY_KEY` do `.env` (valor `sk-helpdesk-app-0001`). Já verifiquei que, pelo gateway, com `max_tokens: 2000` e a mensagem `TASK: <task>\n<conteúdo>` como único user message, as 4 tarefas devolvem o mesmo texto da v1.

## Regras inegociáveis
- NÃO altere `tests/characterization/`, `provider-fake/`, `edge/`, `data/`, `gateway/`, `metrics/`, `.env.example`. Não altere `docs/` exceto o arquivo de log `docs/evidence/f05/handoff-log.md` (crie-o).
- NÃO mude rotas, corpos, status HTTP, mensagens de erro nem modo de resposta (tudo continua síncrono e em JSON). Os erros 502 de valor fora do permitido (classification/extraction) e o 422 de `start > end` (report) devem continuar idênticos.
- A mensagem enviada ao modelo continua exatamente `f"TASK: {task}\n{content}"`, como único user message; o conteúdo do relatório continua `"\n".join(f"[{t['id']}] {t['text']}" for t in batch)` em lotes de 150, sequenciais, com a mesma agregação/ordenação de `report.py`.
- Sem cache, circuit breaker, retry, fallback, streaming, async: nada disso é desta fase.
- Não escreva código "para a métrica" (import que só existe para mudar um número). Cada dependência precisa ter motivo de comportamento ou de tipo.

## Alvos, nesta ordem (um commit por alvo aceito)
1. `suggestion`: recebe `gateway: LLMGateway`, declara `CAPABILITY = "helpdesk-suggest"`, deixa de importar `config`/`llm`. Ajuste `ProviderGateway` para mapear as capacidades pelos nomes `helpdesk-*` (renomeie também a de classification de `"classification"` para `"helpdesk-classify"`), mantendo exatamente as chamadas da v1 enquanto ele existir.
2. `extraction`: idem, `CAPABILITY = "helpdesk-extract"`, parse com `json.loads` local.
3. `report` + `tickets`: em `ports.py`, `class TicketSource(Protocol)` com `in_period(self, start: date, end: date) -> list[dict]`. Em `tickets.py`, `class JsonlTicketSource(TicketSource)` que recebe o caminho do arquivo no construtor (mesma leitura de hoje). `report.topics(period, gateway, tickets)` com `CAPABILITY = "helpdesk-topics"` e `TICKETS_PER_CALL = 150` como constante do próprio `report`.
4. `adapters/gateway.py` (crie `app/helpdesk/adapters/__init__.py` vazio): `class GatewayClient(LLMGateway)` — ÚNICO componente que fala com o modelo. Usa o SDK `openai` (`OpenAI(base_url=..., api_key=..., timeout=..., max_retries=0)`), chama `chat.completions.create(model=capability, max_tokens=self._max_tokens, messages=[{"role": "user", "content": f"TASK: {task}\n{content}"}])` e devolve `response.choices[0].message.content`. Construtor recebe `base_url`, `api_key`, `timeout` (segundos) e `max_tokens` (2000). Em `main.py` (ponto de composição): leia do ambiente `GATEWAY_BASE_URL`, `GATEWAY_API_KEY`, `GATEWAY_TIMEOUT_SECONDS` (padrão "60") e `TICKETS_FILE` (padrão "/data/tickets.jsonl"); monte `GatewayClient` e `JsonlTicketSource` e injete nas rotas. Só `main.py` importa `adapters.gateway` e `tickets`.
5. Dissolver `config.py` e `llm.py` (apagar os dois). `app/requirements.txt`: remover `anthropic`; manter `fastapi==0.115.6`, `uvicorn==0.34.0`, `openai==3.19.0`; ADICIONAR `pydantic==2.14.1` e `pydantic_core==2.50.1` (versões da imagem da v1, para as mensagens 422 não mudarem). `compose.yaml`, serviço `app`: remover `env_file: .env` e adicionar `environment:` com `GATEWAY_BASE_URL: http://gateway:4000` e `GATEWAY_API_KEY: ${HELPDESK_GATEWAY_KEY}` (não mexa nos outros serviços do compose).

## Juízes (rode TODOS após cada alvo; só faça o commit do alvo se os quatro passarem)
1. Comportamento: `docker compose up -d --build --wait app && .venv/Scripts/python -m pytest tests/characterization -q` → precisa dar `17 passed`. No alvo 5, use `docker compose up -d --build --wait`.
2. Suíte intocada: `git diff --exit-code v1-coupled -- tests/characterization/` → vazio.
3. Estrutura: `.venv/Scripts/python metrics/coupling.py app/helpdesk --name wip --out-dir /tmp/f05-wip` → nenhum componente na zona de dor (A<0.5 E I<0.5 E D>=0.5) exceto `schemas` (e, enquanto existirem, `config`/`llm`); nenhuma feature com dependência para componente concreto que não seja `schemas`.
4. Restrições (obrigatórias a partir do alvo 5): `grep -rE "gpt-fake|claude-fake" app/` vazio; `grep -rE "FAKE_OPENAI_KEY|FAKE_ANTHROPIC_KEY|sk-fake-openai|sk-ant-fake" app/` vazio; nenhum import de `adapters`/`tickets` fora do `main.py`; `docker compose exec app env | grep -E "FAKE_|sk-fake|sk-ant"` vazio.
Se um juiz falhar: corrija e rode de novo; registre a rejeição e o motivo no log. Não "conserte" testes nem a métrica.

## Commits
Um por alvo, mensagem Conventional Commits em português; no corpo, a linha da métrica dos componentes afetados e "17 passed"; terminar com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. `git add` com caminhos explícitos (nunca `-A`; nunca `.env`).

## Log (docs/evidence/f05/handoff-log.md)
Para cada alvo: o que mudou, saída resumida dos 4 juízes (inclua o CSV da métrica), rejeições/iterações e motivo. Commit do log junto com o último alvo.

## Resposta final
Commits (hash + mensagem), CSV final da métrica, resultado final dos 4 juízes, rejeições e desvios das instruções (com motivo). Seja factual; não declare nada que você não executou.
