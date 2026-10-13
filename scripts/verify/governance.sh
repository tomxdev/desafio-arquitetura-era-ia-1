#!/usr/bin/env bash
# Roteiro de governança (README): recusa por orçamento e por limite de requisições, ANTES do provider.
# Usa as chaves de demonstração do .env.example direto no gateway (localhost:4000).
source "$(dirname "$0")/_lib.sh"
BUDGET_KEY=${GATEWAY_DEMO_BUDGET_KEY:-sk-demo-budget-0001}
RPM_KEY=${GATEWAY_DEMO_RPM_KEY:-sk-demo-rpm-0001}
BODY='{"model": "helpdesk-classify", "messages": [{"role": "user", "content": "TASK: classify\nMeu pedido atrasou"}]}'

gw() { # chave → "status" e corpo em "$BODY_FILE"
  curl -s -o "$BODY_FILE" -w '%{http_code}' "$GATEWAY/chat/completions" \
    -H "Authorization: Bearer $1" -H 'Content-Type: application/json' -d "$BODY"
}

attempt() { # rótulo chave status_esperado
  local before after status
  before=$(call_count); status=$(gw "$2"); sleep 0.5; after=$(call_count)
  echo "$1: status=$status | /admin/calls $before -> $after | $(head -c 150 "$BODY_FILE")"
  check "$1 → $3" "$([ "$status" = "$3" ] && echo 0 || echo 1)"
  if [ "$3" = 200 ]; then
    check "$1 chegou ao provider (+1 chamada)" "$([ "$after" -eq $((before + 1)) ] && echo 0 || echo 1)"
  else
    check "$1 NÃO chegou ao provider (contador igual)" "$([ "$after" -eq "$before" ] && echo 0 || echo 1)"
  fi
}

echo "# Governança ($(date -u +%FT%TZ))"
reset_provider

echo "## Orçamento: chave demo-budget (max_budget US\$ 0,0001; uma classificação custa ~US\$ 0,00013)"
spend=$(curl -s "$GATEWAY/key/info?key=$BUDGET_KEY" -H "Authorization: Bearer ${LITELLM_MASTER_KEY:-sk-litellm-master-0001}" | python -c "import sys,json;print(json.load(sys.stdin)['info']['spend'])")
echo "gasto atual da chave: US\$ $spend"
if python -c "import sys; sys.exit(0 if float('$spend') < 0.0001 else 1)"; then
  attempt "orçamento, 1ª requisição (dentro do orçamento)" "$BUDGET_KEY" 200
fi
attempt "orçamento, requisição após estourar" "$BUDGET_KEY" 429
grep -q budget_exceeded "$BODY_FILE"; check "motivo: budget_exceeded" $?

echo "## Limite de requisições: chave demo-rpm (2 por minuto)"
echo "(aguardando a janela de 1 minuto zerar, para o roteiro ser repetível)"; sleep 61
attempt "limite, 1ª requisição" "$RPM_KEY" 200
attempt "limite, 2ª requisição" "$RPM_KEY" 200
attempt "limite, 3ª requisição no mesmo minuto" "$RPM_KEY" 429
grep -qi "rate limit" "$BODY_FILE"; check "motivo: rate limit" $?

finish
