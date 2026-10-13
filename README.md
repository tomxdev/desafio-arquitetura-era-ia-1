# Helpdesk com IA: da integração frágil à arquitetura resiliente

Entrega do desafio [Da integração frágil à arquitetura resiliente](https://github.com/devfullcycle/desafio-arquitetura-era-ia-1) (o enunciado completo continua no `README.md` do repositório base). O plano de execução e a rastreabilidade dos critérios estão em [`docs/implementation-master-plan.md`](docs/implementation-master-plan.md) e [`docs/acceptance-matrix.md`](docs/acceptance-matrix.md).

> **Estado atual: v1 (aplicação recebida, sem alterações em `app/`).** As seções marcadas como *em construção* são preenchidas nas fases seguintes do plano.

## Visão geral

*Em construção (F08).* Hoje o `app/` é exatamente o do repositório base: cada feature chama o SDK do provider direto, com nome de modelo e chave no código, tudo de forma síncrona. Quando um provider cai, as features presas a ele param, e só elas: F1/F4 dependem do `openai`, e F2/F3 do `anthropic` (ver dor 3).

## Diagnóstico da v1

Ambiente: `cp .env.example .env && docker compose up -d --build --wait`, provider simulado em modo normal salvo indicação, todas as requisições **pela borda** (`localhost:8000`). Os comandos estão versionados em [`scripts/diagnostics/`](scripts/diagnostics/), e as saídas brutas em [`docs/evidence/f01/`](docs/evidence/f01/). Medido em 2026-10-13 (Docker Desktop 29.7.2, Windows 11).

> **Nota sobre Windows:** acentos passados como argumento do `curl` no Git Bash/PowerShell chegam corrompidos e a aplicação responde `400 {"detail":"There was an error parsing the body"}`. Por isso, todos os comandos enviam o corpo de arquivo: `--data-binary @scripts/diagnostics/payloads/<arquivo>.json`.

### Linha de base (modo normal)

`bash scripts/diagnostics/features.sh` ([evidência](docs/evidence/f01/features/))

| Feature | Rota | Status | Tempo total pela borda | Chamadas ao provider |
|---|---|---|---|---|
| F1 Classificar | `POST /tickets/classification` | 200 `{"ticket_id":"TK-00042","category":"delivery","priority":"high"}` | 1,08 s | 1 × `openai/gpt-fake-large` |
| F2 Sugerir | `POST /tickets/reply-suggestion` | 200, 2.606 bytes, `application/json` | **15,96 s** (1º byte também em 15,96 s) | 1 × `anthropic/claude-fake-large`, 606 tokens de saída |
| F3 Relatório (1 dia) | `POST /reports/topics` `2026-08-01`→`2026-08-01` | 200, `total_tickets: 137` | 9,85 s | 1 × `anthropic/claude-fake-large` (6.132 tokens in) |
| F4 Extrair | `POST /tickets/extraction` | 200 `{"order_number":"#481516","product":null}` | 1,08 s | 1 × `openai/gpt-fake-large` |

### Dor 1: o relatório do mês não chega

**Comando:** `bash scripts/diagnostics/pain1_report.sh`, que faz `POST /reports/topics` com `{"start":"2026-08-01","end":"2026-08-31"}` e depois acompanha `GET localhost:8090/admin/calls` a cada 15 s.

**Observado** ([relatório](docs/evidence/f01/pain1-report.txt), [linha do tempo](docs/evidence/f01/pain1-calls-after-504.txt), [resumo](docs/evidence/f01/pain1-summary.txt), [registro bruto](docs/evidence/f01/pain1-admin-calls.json)):

- A borda responde **`504 Gateway Time-out` em 30,03 s** (página HTML do nginx). O cliente não recebe nada do relatório.
- No momento do 504, o provider tinha recebido **4** das chamadas `topics`. A aplicação **continuou**: o `/admin/calls` foi de 4 para **34 chamadas** (5.000 tickets / 150 por lote), todas `claude-fake-large`, status 200, ~9,7 s cada, uma depois da outra. A última terminou às 15:09:26, **331 s** depois da primeira e ~5 min depois de a borda desistir.
- Custo, pelos preços do `provider-fake/README.md`: 222.114 tokens de entrada + 12.162 de saída = **US$ 0,85** por relatório. **30 chamadas (US$ 0,75, 88%) começaram depois do 504**, pagas sem ninguém para receber o resultado ("desistir não é cancelar").

**Causa:**

- `app/helpdesk/main.py:30-32`: a rota `POST /reports/topics` é síncrona e só devolve o relatório inteiro no fim.
- `app/helpdesk/report.py:15-18`: o loop processa os lotes **sequencialmente**, 34 × ~9,7 s ≈ 330 s, muito acima da paciência da borda.
- `edge/nginx.conf` (`proxy_read_timeout 30s`): sem nenhum byte em 30 s, a borda corta com 504. O timeout mais curto da cadeia vence, e não é o da aplicação.
- Nada liga o fim da conexão ao trabalho em andamento: a thread do FastAPI segue chamando o provider depois que o cliente se foi.

### Dor 2: a sugestão deixa o atendente esperando sem ver nada

**Comando:** `bash scripts/diagnostics/pain2_suggestion.sh`, que faz `curl -sN -X POST localhost:8000/tickets/reply-suggestion` medindo o tempo até o primeiro byte.

**Observado** ([evidência](docs/evidence/f01/pain2-suggestion.txt)): `status=200 content_type=application/json` **ttfb = 15,96 s, total = 15,96 s**. O primeiro byte só chega quando o texto inteiro (2.606 bytes) está pronto. No `/admin/calls`: 1 chamada `claude-fake-large`, `stream: false`, 606 tokens de saída, `duration_ms: 15951`. É coerente com o README do provider: 800 ms até o primeiro token + 606 tokens a 40 tok/s ≈ 16 s.

**Causa:**

- `app/helpdesk/llm.py:20-26`: `call_anthropic` usa `messages.create` **sem streaming** e só retorna o texto completo.
- `app/helpdesk/suggestion.py:5-7` e `app/helpdesk/main.py:20-22`: a rota devolve um JSON único (`ReplySuggestion`), então não há como mostrar o texto aos poucos, embora o provider gere token a token.

### Dor 3: com um provider fora do ar ou travado, parte do helpdesk para

**Comando:** `bash scripts/diagnostics/pain3_provider_down.sh`, que usa `POST localhost:8090/admin/failures` para derrubar um provider de cada vez e chama as features pela borda.

**Observado** ([evidência](docs/evidence/f01/pain3-provider-down.txt), [padrões dos SDKs](docs/evidence/f01/sdk-defaults.txt)):

| Cenário | F1 | F4 | F2 | F3 (1 dia) | `/admin/calls` |
|---|---|---|---|---|---|
| `openai` em `error_500` | **500** em 1,19 s | **500** em 1,44 s | 200 | 200 | **3 chamadas por requisição** (1 + 2 retries do SDK, com ~0,4 s e ~0,8 s de espera), todas 500 |
| `anthropic` em `error_500` | 200 | — | **500** em 1,24 s | **500** em 1,51 s | 3 chamadas `claude-fake-large` 500 por requisição |
| `openai` em `timeout` | **504 da borda em 30,03 s** | — | — | — | 1 chamada `classify` com `duration_ms: null` (ainda aberta) |

- A aplicação devolve `500 Internal Server Error` em texto puro (exceção não tratada do SDK), sem dizer o que falhou.
- Os padrões dos SDKs instalados (`openai 3.19.0`, `anthropic 1.8.0`): **`DEFAULT_MAX_RETRIES = 2`** e **`DEFAULT_TIMEOUT = Timeout(connect=5.0, read=600, ...)`**. Uma chamada travada pode prender a requisição por até 3 × 600 s, contra os **30 s** da borda.
- **Requisição zumbi** ([evidência](docs/evidence/f01/pain3-zombie.txt)): a F1 com `openai` em `timeout` recebeu 504 da borda às 15:12:23. Logo depois, o provider voltou ao normal (`/admin/reset`, que também limpa o registro) e nenhuma requisição nova foi feita. Mesmo assim, às **15:16:53** o `/admin/calls` registrou uma nova chamada `openai/gpt-fake-large classify` (status 200). Era o **retry do SDK**: o provider segurou a primeira tentativa por 300 s, respondeu 504, e o SDK tentou de novo, ~5 min depois de o cliente ter desistido.

**Causa:**

- `app/helpdesk/config.py:9-13`: cada feature está **fixada** num provider (`CLASSIFICATION_MODEL`/`EXTRACTION_MODEL` no `gpt-fake-large`; `SUGGESTION_MODEL`/`REPORT_MODEL` no `claude-fake-large`), sem destino alternativo, embora os dois `large` sejam equivalentes.
- `app/helpdesk/llm.py:8-9`: clientes criados **sem `timeout` nem `max_retries`**, valendo os padrões acima (600 s, 2 retries).
- `app/helpdesk/llm.py:12-26`: `call_openai`/`call_anthropic` não tratam erro nem tentam outro provider; a exceção vira 500 genérico.

### Dor 4: trocar o modelo de uma feature exige mudar código e reconstruir

**Comando:** `bash scripts/diagnostics/pain4_model_swap.sh`, que troca o modelo da F1 de `gpt-fake-large` para `gpt-fake-mini` **temporariamente** e restaura no fim.

**Observado** ([evidência](docs/evidence/f01/pain4-model-swap.txt)):

| Passo | Ação | Imagem / início do container `app` | Modelo da F1 no `/admin/calls` |
|---|---|---|---|
| 0 | estado inicial | `ba55f9b0…` / 15:00:06 | `gpt-fake-large` |
| 1 | editar `app/helpdesk/config.py:10` (`CLASSIFICATION_MODEL = "gpt-fake-mini"`) | — | — |
| 2 | `docker compose restart app` | `ba55f9b0…` (mesma) / 15:17:23 | **`gpt-fake-large`**: o restart não troca o modelo |
| 3 | `docker compose up -d --build --wait app` (7 s neste host) | **`ccfa4c0c…` (nova)** / 15:17:32 | `gpt-fake-mini` |
| 4 | `git checkout -- app/` + rebuild | `1046826c…` / 15:17:39 | `gpt-fake-large`; `git diff --quiet upstream/main -- app/` OK |

Trocar o modelo de uma única feature exigiu editar código, gerar uma imagem nova e recriar o container da aplicação, ou seja, um deploy (com a indisponibilidade do app durante a recriação). A alteração foi desfeita: `app/` continua idêntico ao do repositório base.

**Causa:**

- `app/helpdesk/config.py:10-13`: os nomes **físicos** dos modelos são constantes no código.
- `app/Dockerfile` (`COPY helpdesk ./helpdesk`): o código é copiado para dentro da imagem, então mudar uma constante exige **rebuild** e recriação do container (um deploy).
- `app/helpdesk/config.py:3-4` + `compose.yaml` (`env_file: .env` no serviço `app`): as chaves dos dois providers também vivem na aplicação.

### Large × mini (insumo para a política de fallback)

**Comando:** `python scripts/diagnostics/compare_models.py`, que chama o provider direto (`localhost:8090`) nas quatro tarefas, com os quatro modelos, numa amostra fixa de `data/tickets.jsonl` ([resumo](docs/evidence/f01/models-compare/summary.md), CSVs na mesma pasta).

| Tarefa | Amostra | Mini vs. large | Tempo (large → mini) |
|---|---|---|---|
| `classify` | 40 tickets | **idêntico** em 40/40 | 1,1 s → 0,4 s |
| `extract` | 40 tickets | **diverge em 9/40**: em 4, devolve o número da **nota fiscal** como `order_number` (ex.: TK-00002 "nota fiscal 530720 … pedido #605065" → mini `#530720`), em formato válido, que passa por `extraction.py:16`; em 6, perde o `product` | 1,1 s → 0,4 s |
| `suggest` | 5 tickets | texto válido, mas com ~44% do tamanho (≈1.070 vs. ≈2.430 caracteres) | 16 s → 2,1 s |
| `topics` | 1 lote de 150 | **idêntico** (mesmos temas, counts e exemplos) | 9,8 s → 2,7 s |

Os dois `large` deram saídas idênticas entre si nas quatro tarefas.

## Como rodar

```bash
cp .env.example .env
docker compose up -d --build --wait
curl -s localhost:8000/health
```

Diagnóstico da v1 (exige o compose no ar; Git Bash ou bash):

```bash
bash scripts/diagnostics/features.sh            # F1–F4 em modo normal
bash scripts/diagnostics/pain1_report.sh        # dor 1 (~6 min)
bash scripts/diagnostics/pain2_suggestion.sh    # dor 2
bash scripts/diagnostics/pain3_provider_down.sh # dor 3
bash scripts/diagnostics/pain4_model_swap.sh    # dor 4 (altera e restaura app/)
python scripts/diagnostics/compare_models.py    # large × mini
```

Testes de caracterização (fixam o comportamento da `v1-coupled`; rodam contra o compose, pela borda):

```bash
python -m venv .venv && source .venv/Scripts/activate   # Linux/macOS: source .venv/bin/activate
pip install -r tests/requirements.txt
python -m pytest tests/characterization -q
```

A suíte (`tests/characterization/`) tem 17 casos: corpo inteiro, status e `Content-Type` das 4 features, mais pelo menos um erro de entrada por feature. Cada teste começa com `POST localhost:8090/admin/reset`. As URLs podem ser trocadas com `HELPDESK_BASE_URL` e `PROVIDER_ADMIN_URL`.

Métrica de acoplamento (Ca, Ce, I, A, D pela régua do requisito 3; grava `metrics/results/<rótulo>.csv` e `.png`):

```bash
pip install -r metrics/requirements.txt
python metrics/coupling.py app/helpdesk --name main          # mede o checkout atual
git worktree add ../v1 v1-coupled                             # mede uma tag a partir de um checkout dela
python metrics/coupling.py ../v1/app/helpdesk --name v1-coupled
git worktree remove ../v1
python -m pytest metrics/tests -q                             # testes do script (inclui o oráculo da v1)
```

## Métrica

Script: [`metrics/coupling.py`](metrics/coupling.py); régua e interpretações no [ADR 0008](docs/adr/0008-medir-acoplamento-pela-regua-fixa.md). *Leitura de v2 e main: em construção (F05/F08).*

### v1-coupled

![A × I da v1-coupled](metrics/results/v1-coupled.png)

[`metrics/results/v1-coupled.csv`](metrics/results/v1-coupled.csv): nenhum componente tem abstração (A = 0 em todo o pacote), então a posição de cada um no gráfico depende só da instabilidade.

- **Zona de dor:** `config` (Ca 6, D 1,00), `llm` (Ca 4, I 0,20, D 0,80) e `schemas` (Ca 5, D 1,00). `config` e `llm` são exatamente os detalhes voláteis do diagnóstico (nome do modelo, provider, chave, SDK) e são **concretos e muito usados**: qualquer troca de modelo ou provider mexe neles e se propaga para as quatro features. `schemas` são os tipos do contrato HTTP: estáveis por natureza (decisão no ADR 0008, na F08).
- **Features** (`classification`, `suggestion`, `extraction`: I 0,75; `report`: I 0,80) e `main` (I 1,00) ficam perto da Main Sequence só por serem instáveis: dependem diretamente de `llm` e `config` concretos.
- `tickets` (I 0,50, D 0,50) fica na borda da zona, sem estar nela (I não é < 0,5).

## Tabela de capacidades

*Em construção (F05/F06).*

## Tabela de fallback

*Em construção (F06).*

## Fluxos

*Em construção (F07).*

## Troca de modelo

*Em construção (F06).* Na v1, ver a dor 4.

## Roteiro de governança

*Em construção (F06).*

## Mapa de decisões

*Em construção (F08).*
