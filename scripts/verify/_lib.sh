#!/usr/bin/env bash
# Funções comuns dos roteiros de verificação (F06+). Exigem o compose no ar e python no PATH.
set -u
export MSYS_NO_PATHCONV=1   # Git Bash: não converter "/tickets/..." em caminho do Windows
export PYTHONIOENCODING=utf-8   # saída UTF-8 dos python -c no Windows (acentos nas evidências)
cd "$(dirname "${BASH_SOURCE[0]}")/../.."

EDGE=http://localhost:8000
PROVIDER=http://localhost:8090
GATEWAY=http://localhost:4000
PAYLOADS=scripts/diagnostics/payloads
FAILURES=0
# Relativo ao repo: com MSYS_NO_PATHCONV, o /tmp do Git Bash e o do curl.exe são pastas diferentes.
BODY_FILE=scripts/verify/.last-body

reset_provider() { curl -s -X POST "$PROVIDER/admin/reset" >/dev/null; }
set_failure() { curl -s -X POST "$PROVIDER/admin/failures" -H 'Content-Type: application/json' -d "$1" >/dev/null; }
call_count() { curl -sf "$PROVIDER/admin/calls?last=5000" | python -c "import sys,json;print(len(json.load(sys.stdin)))"; }

# Imprime as chamadas registradas pelo provider (mais antiga primeiro).
show_calls() {
  curl -s "$PROVIDER/admin/calls?last=${1:-20}" | python -c "
import sys, json
for c in reversed(json.load(sys.stdin)):
    print('   ', c['ts'][11:23], c['provider'], c['model'], c['task'], 'status=%s' % c['status'], 'ms=%s' % c['duration_ms'])"
}

# Lista de modelos (mais antiga primeiro) com status: "gpt-fake-large:500 claude-fake-large:200".
call_models() {
  curl -s "$PROVIDER/admin/calls?last=${1:-20}" | python -c "
import sys, json
print(' '.join('%s:%s' % (c['model'], c['status']) for c in reversed(json.load(sys.stdin))))"
}

# feature <rota> <payload> → grava o corpo em "$BODY_FILE" e imprime "status tempo".
# Se a feature for assíncrona (202, F3), acompanha a URL de status até o fim: imprime o status do
# resultado (200) ou "failed", e o tempo total desde o pedido.
feature() {
  local out status total location started
  started=$(python -c "import time; print(time.time())")
  out=$(curl -s -D "$BODY_FILE.h" -o "$BODY_FILE" -w '%{http_code} %{time_total}' -X POST "$EDGE$1" \
    -H 'Content-Type: application/json' --data-binary "@$PAYLOADS/$2")
  read -r status total <<< "$out"
  if [ "$status" = 202 ]; then
    location=$(grep -i '^location:' "$BODY_FILE.h" | tr -d '\r' | awk '{print $2}')
    while :; do
      status=$(curl -s -D "$BODY_FILE.h" -o "$BODY_FILE" -w '%{http_code}' "$EDGE$location")
      if [ "$status" = 303 ]; then
        location=$(grep -i '^location:' "$BODY_FILE.h" | tr -d '\r' | awk '{print $2}')
        status=$(curl -s -o "$BODY_FILE" -w '%{http_code}' "$EDGE$location"); break
      fi
      grep -q '"state":"failed"' "$BODY_FILE" && { status=failed; break; }
      [ "$status" != 200 ] && break
      if python -c "import sys,time; sys.exit(0 if time.time() - $started > 900 else 1)"; then status=timeout; break; fi
      sleep 1
    done
    total=$(python -c "import time; print(f'{time.time() - $started:.3f}')")
  fi
  rm -f "$BODY_FILE.h"
  echo "$status $total"
}

# Começa de um stack quieto: as tarefas de relatório ficam em memória no app e continuam depois que
# o cliente vai embora (ex.: o teste de contrato da F3 deixa o relatório do mês rodando ~5 min), e
# requisições já enviadas ao gateway terminam mesmo após o app reiniciar. Sem isso, chamadas alheias
# entram no /admin/calls do roteiro. Reinicia o app e espera o /admin/calls ficar 15 s sem crescer.
quiesce() {
  local before after stable=0
  docker compose restart app >/dev/null 2>&1; docker compose up -d --wait app >/dev/null 2>&1
  before=$(call_count) || { echo "quiesce: /admin/calls inacessível" >&2; exit 1; }
  while [ "$stable" -lt 15 ]; do
    sleep 3; after=$(call_count) || { echo "quiesce: /admin/calls inacessível" >&2; exit 1; }
    if [ "$after" = "$before" ]; then stable=$((stable + 3)); else stable=0; before=$after; fi
  done
}

check() { # descrição condição(0/1)
  if [ "$2" = 0 ]; then echo "  OK    $1"; else echo "  FALHA $1"; FAILURES=$((FAILURES + 1)); fi
}

finish() {
  reset_provider
  if [ "$FAILURES" -eq 0 ]; then echo "RESULTADO: OK"; else echo "RESULTADO: $FAILURES falha(s)"; exit 1; fi
}
