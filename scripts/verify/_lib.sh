#!/usr/bin/env bash
# Funções comuns dos roteiros de verificação (F06+). Exigem o compose no ar e python no PATH.
set -u
export MSYS_NO_PATHCONV=1   # Git Bash: não converter "/tickets/..." em caminho do Windows
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
call_count() { curl -s "$PROVIDER/admin/calls?last=5000" | python -c "import sys,json;print(len(json.load(sys.stdin)))"; }

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
feature() {
  curl -s -o "$BODY_FILE" -w '%{http_code} %{time_total}' -X POST "$EDGE$1" \
    -H 'Content-Type: application/json' --data-binary "@$PAYLOADS/$2"
}

check() { # descrição condição(0/1)
  if [ "$2" = 0 ]; then echo "  OK    $1"; else echo "  FALHA $1"; FAILURES=$((FAILURES + 1)); fi
}

finish() {
  reset_provider
  if [ "$FAILURES" -eq 0 ]; then echo "RESULTADO: OK"; else echo "RESULTADO: $FAILURES falha(s)"; exit 1; fi
}
