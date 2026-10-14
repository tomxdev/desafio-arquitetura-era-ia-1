# F09: matriz percorrida item a item

Validação em clone limpo da `release/final` (`f9700f5`) num diretório fora do repositório de trabalho, com o compose do repositório de trabalho parado, seguindo só o README: [`fresh-final/run.log`](fresh-final/run.log).

Primeira validação (`5144183`): subiu e passou nas suítes, mas `governance.sh` e `fallback.sh` falharam quando rodados logo depois do `pytest` ([`fresh-before-fix/`](fresh-before-fix/)). A causa é a tarefa do mês deixada pelo teste de contrato da F3. A correção está no PR #14 (`quiesce`), provada em [`readme-order-rerun.txt`](readme-order-rerun.txt) e no clone limpo final.

| Item | Verificação executada | Resultado | Evidência |
|---|---|---|---|
| AC-RDM-02, ST-03 | `cp .env.example .env && docker compose up -d --build --wait`; `curl localhost:8000/health` | 5 serviços saudáveis; `200`, sem passo manual | `fresh-clone.log`, `fresh-final/run.log` |
| AC-MET-02 | script da `main` sobre checkouts (worktree) de `v1-coupled`, `v2-decoupled` e do próprio clone | os três CSVs idênticos aos versionados | `fresh-final/run.log`, `fresh-readme-run.log` |
| AC-RDM-03, RS-01 | `git diff --quiet upstream/main origin/main` e `origin/release/final -- provider-fake/ edge/ data/` | sem diferença | `milestones.txt` |
| AC-GW-01 | `grep -rE "gpt-fake\|claude-fake" app/` no clone limpo | vazio | `static-checks.txt` |
| AC-GW-02, RS-03 | grep de chaves em `app/`; `docker compose exec app env`; `docker compose config` do `app` | vazio; só `GATEWAY_API_KEY` e `GATEWAY_BASE_URL`; sem `env_file`; volume só `data` | `static-checks.txt` (v2: `docs/evidence/f05/`) |
| RS-02 | `grep -rnE "provider-fake\|8090" app/`; roteiros contam `/admin/calls` vindos do gateway | vazio; roteiros OK | `static-checks.txt`, `fresh-final/*.txt` |
| RS-04, TC-04 | `git log --no-merges v1-coupled..HEAD -- app/`; `python --version` e `pip show fastapi` no container | 8 commits incrementais (piloto + 1 por alvo); Python 3.12.15, FastAPI 0.115.6, `FROM python:3.12-slim` | `refactor-history.txt`, `static-checks.txt` |
| RS-06 | `.env.example` só com chaves fake; imagens do compose | `provider-fake`, `nginx:1.27-alpine`, `ghcr.io/berriai/litellm:v1.102.1`, `postgres:16-alpine` e o `app`; nenhuma API real | `static-checks.txt` |
| RS-08 | revisão dos ADRs | limitação do LiteLLM (sem fallback no meio do stream) documentada no ADR 0007 e resolvida no app com `event: error`, provada no `flows.sh` | `docs/adr/0007-*.md`, `fresh-final/flows.txt` |
| RS-09 | `grep -rniE "cache\|circuit\|rag\b\|guardrail" app/ gateway/` | só `pip --no-cache-dir`, o header `Cache-Control: no-cache` do SSE e um comentário dizendo que circuit breaker está fora do escopo | `static-checks.txt` |
| ST-01 | `gh repo view --json visibility,isFork,parent` | `PUBLIC`, fork de `devfullcycle/desafio-arquitetura-era-ia-1`; `main` final após o PR de release | `repo-visibility.txt` |
| Marcos | comandos da seção 3.6 do plano | `app/` da v1 = base; suíte idêntica v1 → v2; tags anotadas no remoto; v1 ⊂ v2 ⊂ main ⊂ release/final | `milestones.txt`, `tags.txt` |
| Todos os AC-GW, AC-FLOW | `governance.sh`, `fallback.sh`, `model_swap.sh`, `flows.sh` e `pytest` (caracterização + contrato + métrica) no clone limpo | `RESULTADO: OK` nos quatro; 25 passed, 1 skipped | `fresh-final/` |
