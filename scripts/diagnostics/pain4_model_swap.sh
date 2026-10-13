#!/usr/bin/env bash
# F01, dor 4: trocar o modelo de uma feature exige mudar código e reconstruir a aplicação.
# Altera app/ TEMPORARIAMENTE e restaura no fim (git checkout -- app/ + rebuild).
set -u
cd "$(dirname "$0")/../.."
# O passo 4 restaura app/ com `git checkout -- app/`: com alterações locais em app/, elas seriam perdidas.
if ! git diff --quiet -- app/ || ! git diff --cached --quiet -- app/ || [ -n "$(git ls-files --others --exclude-standard -- app/)" ]; then
  echo "app/ tem alterações locais; faça commit ou stash antes de rodar este roteiro." >&2
  exit 1
fi
E=docs/evidence/f01
F1() { curl -s -o /dev/null -X POST localhost:8000/tickets/classification -H "Content-Type: application/json" --data-binary @scripts/diagnostics/payloads/ticket-tk-00042.json -w 'F1 status=%{http_code}\n'; }
last_model() { curl -s "localhost:8090/admin/calls?last=1" | python -c "import sys,json;c=json.load(sys.stdin)[0];print('  /admin/calls ->',c['provider'],c['model'],c['task'])"; }
app_state() { docker inspect -f '  app image={{.Image}} started={{.State.StartedAt}}' "$(docker compose ps -q app)"; }
{
echo "# Dor 4: troca de modelo da F1 ($(date -u +%FT%TZ))"
curl -s -X POST localhost:8090/admin/reset >/dev/null
echo "## Estado inicial"; app_state; F1; last_model
echo; echo "## 1) Editar o código: app/helpdesk/config.py:10"
sed -i 's/CLASSIFICATION_MODEL = "gpt-fake-large"/CLASSIFICATION_MODEL = "gpt-fake-mini"/' app/helpdesk/config.py
git diff -- app/
echo; echo "## 2) Só reiniciar o app NÃO troca o modelo (o código está dentro da imagem)"
echo "\$ docker compose restart app"; docker compose restart app >/dev/null 2>&1; docker compose up -d --wait app >/dev/null 2>&1
app_state; F1; last_model
echo; echo "## 3) Rebuild + recriação do container (deploy)"
echo "\$ docker compose up -d --build --wait app"; s=$(date +%s); docker compose up -d --build --wait app >/dev/null 2>&1; echo "  levou $(( $(date +%s) - s )) s"
app_state; F1; last_model
echo; echo "## 4) Restaurar app/ ao estado do repositório base"
git checkout -- app/
docker compose up -d --build --wait app >/dev/null 2>&1
git diff --quiet upstream/main -- app/ && echo "  git diff --quiet upstream/main -- app/ -> OK (app/ idêntico ao base)"
app_state; F1; last_model
} 2>&1 | tee $E/pain4-model-swap.txt
