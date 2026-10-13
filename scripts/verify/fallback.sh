#!/usr/bin/env bash
# Resiliência (README, Tabela de capacidades e Tabela de fallback), sempre pela borda:
# 1) primário de cada capacidade em error_500 → sucesso no destino equivalente do outro provider,
#    com no máximo 2 tentativas no primário;
# 2) os dois modelos large em error_500 → cada feature como declarado na Tabela de fallback;
# 3) provider primário da F1 em timeout → resposta em até 15 s.
source "$(dirname "$0")/_lib.sh"

primary_down() { # feature rota payload modelo_primário provider_primário modelo_fallback
  reset_provider
  set_failure "{\"provider\": \"$5\", \"model\": \"$4\", \"mode\": \"error_500\"}"
  read -r status total < <(feature "$2" "$3")
  local seq; seq=$(call_models 10)
  echo "$1 com $4 em error_500: status=$status total=${total}s | /admin/calls: $seq"
  check "$1 responde 200" "$([ "$status" = 200 ] && echo 0 || echo 1)"
  python - "$seq" "$4" "$6" <<'EOF'
import sys
calls = [c.rsplit(":", 1) for c in sys.argv[1].split()]
primary, fallback = sys.argv[2], sys.argv[3]
tries = [s for m, s in calls if m == primary]
ok = (1 <= len(tries) <= 2 and all(s == "500" for s in tries)
      and calls[-1] == [fallback, "200"] and calls[:len(tries)] == [[primary, s] for s in tries])
sys.exit(0 if ok else 1)
EOF
  check "$1: até 2 tentativas em $4, depois sucesso em $6" $?
}

echo "# Fallback técnico ($(date -u +%FT%TZ))"
primary_down F1 /tickets/classification ticket-tk-00042.json gpt-fake-large openai claude-fake-large
primary_down F2 /tickets/reply-suggestion ticket-tk-00042.json claude-fake-large anthropic gpt-fake-large
primary_down F3 /reports/topics period-1-dia.json claude-fake-large anthropic gpt-fake-large
primary_down F4 /tickets/extraction ticket-tk-00042.json gpt-fake-large openai claude-fake-large

echo "# Sem nenhum modelo large (os dois em error_500)"
no_large() { # feature rota payload status_esperado modelo_final_esperado
  reset_provider
  set_failure '{"provider": "openai", "model": "gpt-fake-large", "mode": "error_500"}'
  set_failure '{"provider": "anthropic", "model": "claude-fake-large", "mode": "error_500"}'
  read -r status total < <(feature "$2" "$3")
  local seq; seq=$(call_models 20)
  echo "$1: status=$status total=${total}s | corpo: $(head -c 120 "$BODY_FILE") | /admin/calls: $seq"
  check "$1 → $4" "$([ "$status" = "$4" ] && echo 0 || echo 1)"
  if [ "$5" = "-" ]; then
    echo "$seq" | grep -q "mini"; check "$1 não usa modelo mini" "$([ $? -ne 0 ] && echo 0 || echo 1)"
  else
    check "$1 respondida por $5" "$([ "${seq##* }" = "$5:200" ] && echo 0 || echo 1)"
  fi
}
no_large F1 /tickets/classification ticket-tk-00042.json 200 gpt-fake-mini
no_large F2 /tickets/reply-suggestion ticket-tk-00042.json 200 claude-fake-mini
no_large F3 /reports/topics period-1-dia.json 200 claude-fake-mini
no_large F4 /tickets/extraction ticket-tk-00042.json 503 -

echo "# Provider primário da F1 (openai) em timeout"
reset_provider
set_failure '{"provider": "openai", "mode": "timeout"}'
read -r status total < <(feature /tickets/classification ticket-tk-00042.json)
echo "F1: status=$status total=${total}s | /admin/calls: $(call_models 5)"
check "F1 responde (200 ou erro explícito) em até 15 s" \
  "$(python -c "import sys; sys.exit(0 if '$status' in ('200','503') and float('$total') <= 15 else 1)" && echo 0 || echo 1)"
check "sem 504 da borda" "$([ "$status" != 504 ] && echo 0 || echo 1)"

finish
