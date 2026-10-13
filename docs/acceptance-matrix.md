# Matriz de aceite: requisito → fase → teste → evidência

> Fonte: `desafio_arquitetura_ia_helpdesk.md` (seções "Critérios de Aceite", "Requisitos", "Restrições", "Tecnologias obrigatórias", "Estrutura obrigatória do entregável" e "Entregável").
> Plano: `implementation-master-plan.md` (no fork: `docs/`).
> Status: `pending` · `in_progress` · `blocked` · `done`. Só marque `done` com o **caminho de uma evidência real**.
> Caminhos de evidência relativos à raiz do fork. `S` = comando de shell (Git Bash) a partir da raiz do fork com o compose no ar, salvo indicação.

## 1. Critérios de Aceite (obrigatórios, texto do enunciado)

### 1.1 Diagnóstico e caracterização

| ID | Critério | Fase | Verificação | Evidência | Status |
|---|---|---|---|---|---|
| AC-DIAG-01 | A seção "Diagnóstico da v1" do README registra as quatro dores, cada uma com o comando executado, o resultado observado e o trecho de `app/` onde está a causa | F01 (final em F08) | revisão: 4 subseções × {comando, observado com status/tempo/`/admin/calls`, `app/helpdesk/<arq>.py:<linha>`}; `grep -n "Diagnóstico da v1" README.md` | `README.md`, `docs/evidence/f01/pain{1..4}-*.txt` | pending |
| AC-DIAG-02 | A tag `v1-coupled` existe no fork, e nela `app/` é idêntico ao do repositório base | F02 | S: `git ls-remote --tags origin \| grep v1-coupled` e `git diff --quiet upstream/main v1-coupled -- app/ && echo OK` | `docs/evidence/f02/release-v1-checks.txt`, `docs/evidence/f09/tags.txt` | pending |
| AC-DIAG-03 | A suíte fixa o corpo das respostas das 4 features (não só o status), roda com o comando documentado e passa na `v1-coupled` e na `v2-decoupled` | F02, F05 | S: checkout de cada tag → `docker compose down -v && docker compose up -d --build --wait && python -m pytest tests/characterization -q`; revisão: asserts de corpo inteiro (golden) nas 4 features | `docs/evidence/f02/pytest-v1.txt`, `docs/evidence/f05/pytest-v2.txt` | pending |
| AC-DIAG-04 | `git diff v1-coupled v2-decoupled -- tests/characterization/` não mostra diferença | F05 | S: `git diff --exit-code v1-coupled v2-decoupled -- tests/characterization/` | `docs/evidence/f05/release-v2-checks.txt` | pending |

### 1.2 Métrica de acoplamento

| ID | Critério | Fase | Verificação | Evidência | Status |
|---|---|---|---|---|---|
| AC-MET-01 | `metrics/results/` contém, para `v1-coupled`, `v2-decoupled` e `main`, CSV com cabeçalho `component,ca,ce,i,a,d` e gráfico A × I com a Main Sequence | F03 (v1), F05 (v2), F08 (main) | S: `for v in v1-coupled v2-decoupled main; do head -1 metrics/results/$v.csv \| grep -qx 'component,ca,ce,i,a,d' && test -f metrics/results/$v.png && echo $v OK; done`; revisão visual: reta A+I=1 | `metrics/results/*.csv`, `*.png` | pending |
| AC-MET-02 | Rodar o script da `main` sobre um checkout da `v1-coupled` reproduz o CSV versionado | F03, F09 | S: `git worktree add ../v1 v1-coupled && python metrics/coupling.py ../v1/app/helpdesk --name chk --out-dir /tmp/chk && diff /tmp/chk/chk.csv metrics/results/v1-coupled.csv` | `docs/evidence/f09/metric-repro.txt` | pending |
| AC-MET-03 | Os CSVs seguem a régua do req. 3, e a medição da `v1-coupled` bate com a recalculada pelo avaliador | F03 | `pytest metrics/tests -q` (inclui o teste de oráculo da tabela 1.1 do plano); conferência manual de 3 módulos | `docs/evidence/f03/{pytest-metrics.txt,manual-check.md}` | pending |
| AC-MET-04 | Na `main`, nenhum componente na zona de dor (A<0,5, I<0,5 e D≥0,5), exceto os declarados no ADR da métrica como estáveis por natureza, com justificativa; o componente que chama o gateway e as features não podem ser exceção | F08 | S: script de zona de dor (F08, ação 2) × lista do ADR 0008 | `docs/evidence/f08/pain-zone-check.txt`, `docs/adr/0008-*.md` | pending |
| AC-MET-05 | Na `main`, o código que chama o gateway fica em um único componente de `app/`, identificado no README; nenhuma feature o importa; só o ponto de composição depende dele | F05, F08 | S: `grep -rlnE "^(import\|from) (openai\|httpx\|anthropic\|requests)" app/helpdesk` → só `adapters/gateway.py`; `grep -rnE "adapters(\.gateway\| import gateway)" app/helpdesk \| grep -v main.py` → vazio; métrica: Ca do adaptador = {main}; README cita o componente | `docs/evidence/f08/gateway-client-check.txt` | pending |

### 1.3 Plano e refatoração

| ID | Critério | Fase | Verificação | Evidência | Status |
|---|---|---|---|---|---|
| AC-PLAN-01 | `docs/refactoring-plan.md` contém componentes-alvo, estratégia de cada um, critério de pronto, piloto com medição antes e depois, ≥1 revisão justificada e o registro do handoff para o agente | F04, F05 | revisão por checklist das 6 partes | `docs/refactoring-plan.md`, `docs/evidence/f04/pilot-*.csv`, `docs/evidence/f05/handoff-log.md` | pending |
| AC-PLAN-02 | A tag `v2-decoupled` existe, e nela a aplicação já chama os modelos exclusivamente pelo gateway | F05 | S (checkout da tag): greps de AC-GW-01/02; `/admin/calls` após F1 mostra a chamada; `docker compose logs gateway` registra a requisição; o app não tem URL do provider (`! grep -rn "provider-fake" app/`) | `docs/evidence/f05/{greps.txt,admin-calls.json}` | pending |

### 1.4 Gateway

| ID | Critério | Fase | Verificação | Evidência | Status |
|---|---|---|---|---|---|
| AC-GW-01 | `grep -rE "gpt-fake\|claude-fake" app/` não retorna nada na `main` | F05 (mantido até F09) | S: `! grep -rE "gpt-fake\|claude-fake" app/` (também no CI `static`) | `docs/evidence/f05/greps.txt`, `docs/evidence/f09/matrix-run.md` | pending |
| AC-GW-02 | `grep -rE "FAKE_OPENAI_KEY\|FAKE_ANTHROPIC_KEY\|sk-fake-openai\|sk-ant-fake" app/` vazio; `docker compose exec app env` sem as chaves; a definição do `app` em `docker compose config` não recebe essas chaves por variável, `env_file` ou arquivo montado | F05 | S: grep; `docker compose exec app env \| grep -E "FAKE_\|sk-fake\|sk-ant"` (vazio); `docker compose config --format json` → bloco `app` sem `env_file`, sem as chaves, volumes só `./data` | `docs/evidence/f05/{greps.txt,app-env.txt,compose-config-app.json}` | pending |
| AC-GW-03 | Seguindo o README, trocar o modelo físico de uma capacidade exige alterar só a config do gateway e reiniciar só o `gateway`; a próxima chamada aparece em `/admin/calls` com o novo modelo, e o `app` não foi reiniciado | F06 | S: `bash scripts/verify/model_swap.sh` (edita `gateway/config.yaml`, `docker compose restart gateway`, chama a feature, confere o modelo em `/admin/calls`, compara `StartedAt` do app antes/depois, reverte) | `docs/evidence/f06/model-swap.txt` | pending |
| AC-GW-04 | O roteiro de governança do README mostra uma recusa por orçamento e outra por limite de requisições, e o número de chamadas em `/admin/calls` não aumenta com as recusas | F06 | S: `bash scripts/verify/governance.sh` (contagens antes/depois de cada recusa) | `docs/evidence/f06/governance.txt` | pending |
| AC-GW-05 | Com o provider primário de uma capacidade em `error_500`, a feature responde com sucesso, e `/admin/calls` mostra as tentativas no primário (≤ máximo declarado no README) seguidas do sucesso no destino equivalente do outro provider | F06 | S: `bash scripts/verify/fallback.sh` (as 4 capacidades) | `docs/evidence/f06/fallback-*.json` | pending |
| AC-GW-06 | Com os dois `large` em `error_500`, cada uma das 4 features se comporta exatamente como declarado na tabela de fallback do README | F06 (revalidado em F07) | S: `{"provider":"openai","model":"gpt-fake-large","mode":"error_500"}` + idem `claude-fake-large`; chamar F1–F4 pela borda; comparar status/corpo/modelos em `/admin/calls` com a tabela | `docs/evidence/f06/no-large.json`, `docs/evidence/f07/no-large-final.json` | pending |

### 1.5 Fluxos de chamada (medidos pela borda, `localhost:8000`)

| ID | Critério | Fase | Verificação | Evidência | Status |
|---|---|---|---|---|---|
| AC-FLOW-01 | F1 entrega o resultado completo em até 3 s | F07 | S: `curl -s -o /dev/null -w '%{http_code} %{time_total}\n' -X POST localhost:8000/tickets/classification ...` → 200 e ≤ 3,0 (5 execuções) | `docs/evidence/f07/f1-timing.txt` | pending |
| AC-FLOW-02 | `curl -N` na F2 mostra o primeiro trecho em até 1,5 s, e o primeiro trecho chega antes da metade do tempo total | F07 | S: `python scripts/verify/measure_sse.py` (first_chunk_s, total_s) + `curl -N` com timestamps por linha | `docs/evidence/f07/f2-sse-timing.txt` | pending |
| AC-FLOW-03 | O pedido da F3 para `2026-08-01`–`2026-08-31` responde em até 1 s, e o relatório obtido depois tem `total_tickets` = 5000, com as chamadas `topics` registradas em `/admin/calls` | F07 | S: POST com `-w %{time_total}` (≤ 1 s, 202); polling até 303; GET do resultado → `total_tickets == 5000`; `/admin/calls?last=100` filtrado por `task=topics` (34 chamadas esperadas [HIPÓTESE], mais retries se houver) | `docs/evidence/f07/{f3-accept.txt,f3-poll.log,f3-result.json,f3-admin-calls-topics.json}` | pending |
| AC-FLOW-04 | Com os dois providers inteiros em `error_500`, um novo pedido da F3 chega a estado de falha visível ao cliente, com motivo, em até 60 s | F07 | S: `{"provider":"openai","mode":"error_500"}` + `{"provider":"anthropic","mode":"error_500"}`; POST; polling com timestamps até `{"state":"failed","reason":...}`; Δt ≤ 60 s | `docs/evidence/f07/f3-both-down.txt` | pending |
| AC-FLOW-05 | Com o provider primário da F1 em `timeout`, a F1 responde (sucesso via fallback ou erro explícito) em até 15 s | F06/F07 | S: `{"provider":"openai","mode":"timeout"}` (ou o primário declarado); `curl -w '%{http_code} %{time_total}'` ≤ 15 s | `docs/evidence/f07/f1-timeout.txt` | pending |
| AC-FLOW-06 | Nenhuma das verificações acima produz `504` da borda | F07, F09 | S: `bash scripts/verify/flows.sh` agrega todos os status e falha se encontrar 504 da borda (corpo HTML do nginx) | `docs/evidence/f07/no-504.txt` | pending |
| AC-FLOW-07 | Cada modo segue o contrato do padrão do req. 6; se a F2 usa streaming, com o primário dela em `midstream_error` o cliente recebe um evento `error` no formato de Contratos sugeridos | F07 | S: `curl -sN` na F2 com `{"provider":"anthropic","mode":"midstream_error"}` (ou o primário declarado) → `Content-Type: text/event-stream`, linhas `data: {"chunk":...}`, `event: error` + `data: {"ticket_id":...,"message":...}` e fim do stream; F3: 202/Location/Retry-After, 200 com `state`, 303 com Location; `pytest tests/contract -q` | `docs/evidence/f07/{f2-midstream.txt,f3-poll.log}`, `tests/contract/` | pending |

### 1.6 Decisões

| ID | Critério | Fase | Verificação | Evidência | Status |
|---|---|---|---|---|---|
| AC-ADR-01 | `docs/adr/` contém os ADRs mínimos do req. 7, cada um com a linha `Nível:` preenchida | F08 | S: loop de `grep -E "^- Nível: (corporativa\|solução\|software)$"`; checklist dos 6 temas (gateway, capacidades, execução, fallback, governança, métrica) | `docs/evidence/f08/adr-levels.txt` | pending |
| AC-ADR-02 | Pelo menos um ADR em cada nível (corporativa, solução, software) | F08 | S: `grep -h "^- Nível:" docs/adr/0*.md \| sort \| uniq -c` → 3 valores | `docs/evidence/f08/adr-levels.txt` | pending |
| AC-ADR-03 | O ADR de fallback traz, para cada feature, a decisão sobre o modelo fraco e a evidência observada no provider simulado que a sustenta | F06, F08 | revisão: 4 seções, cada uma citando `docs/evidence/f01/models-compare/*` e o resultado de AC-GW-06 | `docs/adr/0006-*.md` | pending |
| AC-ADR-04 | O ADR de execução tem uma seção por feature, cada uma citando as características do contrato que levaram à decisão, e o comportamento implementado bate com ele | F07, F08 | revisão + AC-FLOW-01..07 verdes | `docs/adr/0007-*.md` | pending |

### 1.7 README e consistência geral

| ID | Critério | Fase | Verificação | Evidência | Status |
|---|---|---|---|---|---|
| AC-RDM-01 | O README contém todas as seções listadas em Entregável | F08 | S: loop das 10 seções (F08, seção 8) | `docs/evidence/f08/readme-sections.txt` | pending |
| AC-RDM-02 | `cp .env.example .env && docker compose up -d --build --wait` na `main` sobe tudo, e `curl -s localhost:8000/health` logo em seguida retorna 200, sem passos manuais | F09 | S: clone limpo da `main` | `docs/evidence/f09/fresh-clone.log` | pending |
| AC-RDM-03 | `provider-fake/`, `edge/` e `data/` não foram alterados | todas (CI `static`), F09 | S: `git diff --quiet upstream/main main -- provider-fake/ edge/ data/` | `docs/evidence/f09/matrix-run.md` | pending |
| AC-RDM-04 | Todo serviço do compose além de `provider-fake`, `edge`, `app` e `gateway` tem um ADR que o justifica a partir de um requisito | F05, F08 | S: `docker compose config --services` × ADRs (ex.: `gateway-db` → ADR 0003; `gateway-init` → ADR 0010, se existir) | `docs/evidence/f08/services-vs-adr.txt` | pending |

## 2. Requisitos (tarefas que não aparecem literalmente nos critérios)

| ID | Requisito | Fase | Verificação | Evidência | Status |
|---|---|---|---|---|---|
| RQ-1.1 | Subir o ambiente e exercitar as 4 features pela borda | F01 | curl de F1–F4 | `docs/evidence/f01/features/*.txt` | pending |
| RQ-1.2 | Não alterar `app/` no diagnóstico (exceto a dor 4, temporária e desfeita antes da tag) | F01, F02 | S: `git diff --quiet upstream/main -- app/` no fim da F01 e na tag | `docs/evidence/f01/pain4-*.txt` | pending |
| RQ-1.3 | Comparar large × mini em cada tarefa (fricção 4) | F01 | `scripts/diagnostics/compare_models.py` | `docs/evidence/f01/models-compare/` | pending |
| RQ-1.4 | Identificar timeout e retries padrão dos SDKs e comparar com os 30 s da borda (fricção 3) | F01 | `docker compose exec app python -c ...` | `docs/evidence/f01/sdk-defaults.txt` | pending |
| RQ-1.5 | Mostrar que o 504 não cancela o trabalho (fricção 2) | F01 | `/admin/calls` após o 504 | `docs/evidence/f01/pain1-calls-after-504.txt` | pending |
| RQ-2.1 | Suíte em `tests/characterization/`, via API HTTP, ≥1 erro de entrada por feature | F02 | revisão + pytest | `tests/characterization/` | pending |
| RQ-2.2 | Suíte roda com um único comando documentado no README, contra o compose | F02 | `python -m pytest tests/characterization -q` no README "Como rodar" | `README.md` | pending |
| RQ-2.3 | Na `main`, a suíte pode ser atualizada para o novo contrato (F2/F3) | F07 | pytest na main | `tests/characterization/`, `tests/contract/` | pending |
| RQ-3.1 | Script em `metrics/` recebe o caminho do código a medir | F03 | CLI `python metrics/coupling.py <path> --name <v>` | `metrics/coupling.py` | pending |
| RQ-3.2 | O script nasce **depois** da tag v1 (mede a tag via worktree) | F03 | S: `git log --diff-filter=A --format=%H -- metrics/coupling.py` não é ancestral de `v1-coupled` (`! git merge-base --is-ancestor <sha> v1-coupled`) | `docs/evidence/f03/script-after-v1.txt` | pending |
| RQ-4.1 | Piloto em um único componente antes de escalar, com medição antes/depois | F04 | plano + CSVs | `docs/evidence/f04/` | pending |
| RQ-4.2 | Refatoração feita com agente de IA; métrica e testes como juízes | F05 | log de handoff | `docs/evidence/f05/handoff-log.md` | pending |
| RQ-4.3 | Na v2, um modelo `large` por trás de cada capacidade; mesmas rotas e modos | F05 | `gateway/config.yaml` na tag; suíte verde | `docs/evidence/f05/` | pending |
| RQ-5.1 | Gateway como serviço `gateway`, config versionada em `gateway/` | F05 | `docker compose config --services`; `ls gateway/` | `compose.yaml`, `gateway/` | pending |
| RQ-5.2 | App usa chave do próprio gateway (virtual key ou equivalente), criada sem passo manual | F05 | S: `up --wait` do zero e F1 200 | `docs/evidence/f05/` | pending |
| RQ-5.3 | Timeout explícito, retry limitado com backoff, fallback técnico para **toda** capacidade | F06 | `gateway/config.yaml` + `fallback.sh` | `docs/evidence/f06/` | pending |
| RQ-5.4 | Número máximo de tentativas por destino (primário, fallback técnico, fraco) declarado no README | F06 | README "Tabela de capacidades" × `/admin/calls` | `README.md`, `docs/evidence/f06/fallback-*.json` | pending |
| RQ-5.5 | Preços dos modelos declarados no gateway (senão o orçamento nunca estoura) | F06 | `/key/info` com `spend > 0` | `docs/evidence/f06/key-info.json` | pending |
| RQ-5.6 | Retries não multiplicados entre SDK/gateway/app | F06 | `/admin/calls` com contagem = declarada | `docs/evidence/f06/fallback-*.json` | pending |
| RQ-5.7 | Cada mecanismo: ADR diz onde ele mora (gateway ou app) | F06, F08 | ADR 0009 | `docs/adr/0009-*.md` | pending |
| RQ-6.1 | F2 continua chegando até completar (`event: end`) | F07 | `measure_sse.py` | `docs/evidence/f07/f2-sse-timing.txt` | pending |
| RQ-6.2 | Async: status `200` com `pending`/`running`/`failed` (com motivo); `303` em `done`; nunca preso em `running` | F07 | `tests/contract` + polling | `docs/evidence/f07/f3-poll.log` | pending |
| RQ-6.3 | Feature síncrona com timeout explícito; responde em ≤ 15 s com provider travado | F07 | F1 e F4 com primário em `timeout` | `docs/evidence/f07/f1-timeout.txt`, `f4-timeout.txt` | pending |
| RQ-6.4 | Testes da `main` atualizados/complementados para o novo contrato | F07 | `pytest tests/contract -q` | `tests/contract/` | pending |
| RQ-6.5 | ADR de execução único, com a pergunta da árvore de decisão por feature | F07, F08 | revisão | `docs/adr/0007-*.md` | pending |
| RQ-7.1 | ADRs: um arquivo por decisão, com contexto, opções, decisão e consequências | F08 | revisão por template | `docs/adr/` | pending |

## 3. Restrições (não negociáveis)

| ID | Restrição | Fase | Verificação | Evidência | Status |
|---|---|---|---|---|---|
| RS-01 | `provider-fake/`, `edge/`, `data/` não alterados | todas | CI `static` + AC-RDM-03 | CI + `docs/evidence/f09/` | pending |
| RS-02 | Na v2 e na main, toda chamada a modelo passa pelo gateway; `app/` não chama o provider-fake | F05+ | `! grep -rn "provider-fake\|8090" app/`; `/admin/calls` só com chamadas originadas pelo gateway (logs do gateway) | `docs/evidence/f05/greps.txt` | pending |
| RS-03 | Na v2 e na main, `FAKE_OPENAI_KEY`/`FAKE_ANTHROPIC_KEY` fora de `app/` e do ambiente do `app` | F05+ | AC-GW-02 (nas duas: checkout da tag v2 e main) | `docs/evidence/f05/`, `docs/evidence/f09/` | pending |
| RS-04 | Refatorar o `app/` existente; sem reescrever do zero nem trocar de linguagem; Python 3.12 + FastAPI | F04–F07 | revisão do histórico (`git log --stat app/`): commits incrementais; `app/Dockerfile` em `python:3.12-*`; `fastapi` em `requirements.txt` | `docs/refactoring-plan.md` | pending |
| RS-05 | Mesma régua de métrica nas três medições | F03, F05, F08 | mesmo `metrics/coupling.py` (sem mudança de régua entre medições: `git log -p metrics/coupling.py` revisado) | `docs/evidence/f09/metric-repro.txt` | pending |
| RS-06 | Avaliação sem provider real nem serviço externo além das imagens públicas do compose | F09 | clone limpo sem rede para APIs reais; `.env.example` só com chaves fake | `docs/evidence/f09/fresh-clone.log` | pending |
| RS-07 | Serviço adicional (além de `app` e `gateway`) tem ADR justificando por requisito | F05, F08 | AC-RDM-04 | `docs/evidence/f08/services-vs-adr.txt` | pending |
| RS-08 | Limitação real do gateway documentada no ADR e resolvida na aplicação | F06, F07 | revisão dos ADRs 0006/0009 (seção "Limitações") | `docs/adr/` | pending |
| RS-09 | Fora de escopo não implementado sem necessidade (cache, RAG, circuit breaker, guardrails, evals, auth) | todas | revisão: `grep -rniE "cache\|circuit\|rag" app/ gateway/` justificado ou vazio | `docs/evidence/f09/matrix-run.md` | pending |

## 4. Tecnologias obrigatórias

| ID | Item | Fase | Verificação | Evidência | Status |
|---|---|---|---|---|---|
| TC-01 | Docker e Docker Compose v2 | F00 | `docker compose version` | `docs/evidence/f00/host-versions.txt` | done |
| TC-02 | Git, com as tags publicadas no fork | F02, F05, F09 | `git ls-remote --tags origin` | `docs/evidence/f09/tags.txt` | pending |
| TC-03 | AI Gateway self-hosted como serviço `gateway` (não SaaS) | F05 | `docker compose config --services` contém `gateway`; imagem pública | `compose.yaml` | pending |
| TC-04 | App em Python 3.12 com FastAPI | F05–F09 | `docker compose exec app python --version`; `pip show fastapi` | `docs/evidence/f09/matrix-run.md` | pending |

## 5. Estrutura obrigatória e entregável

| ID | Item | Fase | Verificação | Evidência | Status |
|---|---|---|---|---|---|
| ST-01 | Fork público no GitHub com a versão final na `main` | F00, F09 | `gh repo view tomxdev/desafio-arquitetura-era-ia-1 --json visibility,isFork,parent` | `docs/evidence/f09/repo-visibility.txt` | in_progress (fork público criado na F00; `main` final na F09) |
| ST-02 | `README.md` substituído pelo do aluno | F01, F08 | revisão | `README.md` | pending |
| ST-03 | `compose.yaml` estendido sobe tudo com um comando | F05–F09 | AC-RDM-02 | `docs/evidence/f09/fresh-clone.log` | pending |
| ST-04 | `.env.example` estendido (basta copiar) | F05, F06 | AC-RDM-02 | `.env.example` | pending |
| ST-05 | `gateway/` com capacidades, fallback, chaves, orçamentos e limites | F05, F06 | revisão de `gateway/config.yaml` + seed | `gateway/` | pending |
| ST-06 | `tests/characterization/` | F02 | existe e passa | `tests/characterization/` | pending |
| ST-07 | `metrics/` com script e `results/` das três versões | F03, F05, F08 | AC-MET-01 | `metrics/` | pending |
| ST-08 | `docs/refactoring-plan.md` | F04, F05 | AC-PLAN-01 | `docs/refactoring-plan.md` | pending |
| ST-09 | `docs/adr/` (um arquivo por decisão) | F05–F08 | AC-ADR-01 | `docs/adr/` | pending |
| ST-10 | Arquivos extras (Dockerfiles, scripts, testes da main, serviços) declarados no compose e no README | F08 | revisão do README "Como rodar" | `README.md` | pending |
| ST-11 | Tags marcam estados reais: v1 = app recebido + suíte; v2 = refatorado atrás do gateway com mesmo comportamento | F02, F05 | AC-DIAG-02/03/04, AC-PLAN-02 | `docs/evidence/f02/`, `docs/evidence/f05/` | pending |
| ST-12 | Campos adicionais em contratos (se houver) documentados no README | F07, F08 | revisão (ex.: `progress` e `reason` no status da F3) | `README.md` | pending |

## 6. Seções obrigatórias do README

| ID | Seção | Conteúdo mínimo | Fase | Status |
|---|---|---|---|---|
| RM-01 | Visão geral | solução em 1–2 parágrafos, incluindo o comportamento quando um provider cai | F08 | pending |
| RM-02 | Diagnóstico da v1 | 4 dores: comando, resultado, causa no código | F01 | pending |
| RM-03 | Como rodar | subida, testes de caracterização e script de métrica, com os comandos exatos | F02, F03, F08 | pending |
| RM-04 | Métrica | leitura dos três gráficos (o que saiu de onde e por quê) e exceções declaradas | F08 | pending |
| RM-05 | Tabela de capacidades | capacidade lógica, feature, modelo primário, fallback técnico, política fraca, máximo de tentativas por destino | F06 | pending |
| RM-06 | Tabela de fallback | por feature: resposta e status sem `large` disponível | F06 | pending |
| RM-07 | Fluxos | por feature: modo escolhido e como consumir, com `curl` exato | F07 | pending |
| RM-08 | Troca de modelo | arquivo, o que alterar, comando | F06 | pending |
| RM-09 | Roteiro de governança | comandos que demonstram recusa por orçamento e por limite | F06 | pending |
| RM-10 | Mapa de decisões | tabela ADR, nível, resumo | F08 | pending |

## 7. Cobertura por fase (resumo)

| Fase | IDs |
|---|---|
| F00 | TC-01, ST-01 (fork) |
| F01 | AC-DIAG-01, RQ-1.1–1.5, RM-02, ST-02 |
| F02 | AC-DIAG-02, AC-DIAG-03 (v1), RQ-2.1, RQ-2.2, ST-06, ST-11, TC-02, RM-03 |
| F03 | AC-MET-01 (v1), AC-MET-02, AC-MET-03, RQ-3.1, RQ-3.2, RS-05 |
| F04 | AC-PLAN-01 (parcial), RQ-4.1, ST-08 |
| F05 | AC-DIAG-03 (v2), AC-DIAG-04, AC-MET-01 (v2), AC-MET-05, AC-PLAN-01, AC-PLAN-02, AC-GW-01, AC-GW-02, AC-RDM-04, RQ-4.2, RQ-4.3, RQ-5.1, RQ-5.2, RS-02, RS-03, RS-07, TC-03, ST-03–05, ST-11 |
| F06 | AC-GW-03–06, AC-ADR-03, AC-FLOW-05 (parcial), RQ-5.3–5.7, RS-08, RM-05, RM-06, RM-08, RM-09 |
| F07 | AC-FLOW-01–07, AC-ADR-04, RQ-2.3, RQ-6.1–6.5, ST-12, RM-07 |
| F08 | AC-MET-01 (main), AC-MET-04, AC-MET-05, AC-ADR-01–04, AC-RDM-01, AC-RDM-04, RQ-7.1, RM-01, RM-04, RM-10, ST-09, ST-10 |
| F09 | AC-RDM-02, AC-RDM-03, AC-MET-02 (reexecução), RS-01, RS-06, RS-09, TC-02, TC-04, ST-01 (final) e revalidação de todos |

**Contagem de controle:** 32 critérios de aceite (4 + 5 + 2 + 6 + 7 + 4 + 4) = AC-DIAG-01..04, AC-MET-01..05, AC-PLAN-01..02, AC-GW-01..06, AC-FLOW-01..07, AC-ADR-01..04, AC-RDM-01..04.
