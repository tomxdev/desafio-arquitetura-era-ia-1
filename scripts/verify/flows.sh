#!/usr/bin/env bash
# Fluxos da main (README, "Fluxos"), medidos pela borda (localhost:8000), com os cenários de falha
# dos critérios. Leva ~7 min (o relatório do mês inteiro roda até o fim). Reinicia o app no início
# para não haver tarefas de relatório de execuções anteriores poluindo o /admin/calls.
source "$(dirname "$0")/_lib.sh"
STATUSES=""
note_status() { STATUSES="$STATUSES $1"; }
now() { date +%s.%N; }
elapsed() { python -c "print(f'{$2 - $1:.2f}')"; }

echo "# Fluxos pela borda ($(date -u +%FT%TZ))"
docker compose restart app >/dev/null 2>&1; docker compose up -d --wait app >/dev/null 2>&1
reset_provider

echo "## F1 síncrono (5 execuções; limite 3 s)"
for i in 1 2 3 4 5; do
  read -r status total < <(feature /tickets/classification ticket-tk-00042.json); note_status "$status"
  echo "F1 #$i: status=$status total=${total}s corpo=$(cat "$BODY_FILE")"
  check "F1 #$i em até 3 s" "$(python -c "import sys; sys.exit(0 if '$status' == '200' and float('$total') <= 3 else 1)" && echo 0 || echo 1)"
done

echo "## F2 streaming: curl -N, com o tempo de cada linha desde o pedido"
t0=$(now)
curl -sN -D "$BODY_FILE.h" -X POST "$EDGE/tickets/reply-suggestion" -H 'Content-Type: application/json' \
  --data-binary "@$PAYLOADS/ticket-tk-00042.json" | python -u -c '
import sys, time
t0 = float(sys.argv[1])  # um único processo carimba cada linha no instante em que ela chega
for raw in sys.stdin.buffer:
    line = raw.decode("utf-8").rstrip("\r\n")
    if line:
        print(f"{time.time() - t0:.2f} {line}", flush=True)' "$t0" > "$BODY_FILE.sse"
status=$(head -1 "$BODY_FILE.h" | awk '{print $2}'); note_status "$status"
first=$(grep -m1 ' data: {"chunk"' "$BODY_FILE.sse" | awk '{print $1}')
total=$(tail -1 "$BODY_FILE.sse" | awk '{print $1}')
echo "status=$status $(grep -i '^content-type' "$BODY_FILE.h" | tr -d '\r') | 1º trecho em ${first}s | fim em ${total}s | $(grep -c ' data: {"chunk"' "$BODY_FILE.sse") trechos"
head -3 "$BODY_FILE.sse" | sed 's/^/    /'; echo "    ..."; tail -2 "$BODY_FILE.sse" | sed 's/^/    /'
check "F2 1º trecho em até 1,5 s" "$(python -c "import sys; sys.exit(0 if float('$first') <= 1.5 else 1)" && echo 0 || echo 1)"
check "F2 1º trecho antes da metade do total" "$(python -c "import sys; sys.exit(0 if float('$first') < float('$total') / 2 else 1)" && echo 0 || echo 1)"
tail -2 "$BODY_FILE.sse" | grep -q 'event: end'; check "F2 termina com event: end" $?

echo "## F2 com o primário (claude-fake-large) em midstream_error"
reset_provider; set_failure '{"provider": "anthropic", "model": "claude-fake-large", "mode": "midstream_error"}'
curl -sN -o "$BODY_FILE" -w '%{http_code}' -X POST "$EDGE/tickets/reply-suggestion" -H 'Content-Type: application/json' \
  --data-binary "@$PAYLOADS/ticket-tk-00042.json" > "$BODY_FILE.code"; status=$(cat "$BODY_FILE.code"); note_status "$status"
echo "status=$status | $(grep -c '"chunk"' "$BODY_FILE") trechos antes da falha | fim do stream:"; tail -3 "$BODY_FILE" | sed 's/^/    /'
tail -3 "$BODY_FILE" | grep -q '^event: error$' && tail -2 "$BODY_FILE" | grep -q '"message": "A geração foi interrompida"'
check "F2 recebe event: error no formato do contrato" $?
echo "    /admin/calls: $(call_models 3)"

echo "## F1 com o provider primário (openai) em timeout (limite 15 s)"
reset_provider; set_failure '{"provider": "openai", "mode": "timeout"}'
read -r status total < <(feature /tickets/classification ticket-tk-00042.json); note_status "$status"
echo "F1: status=$status total=${total}s | /admin/calls: $(call_models 5)"
check "F1 responde em até 15 s" "$(python -c "import sys; sys.exit(0 if '$status' in ('200','503') and float('$total') <= 15 else 1)" && echo 0 || echo 1)"

echo "## F4 sem nenhum modelo large"
reset_provider
set_failure '{"provider": "openai", "model": "gpt-fake-large", "mode": "error_500"}'
set_failure '{"provider": "anthropic", "model": "claude-fake-large", "mode": "error_500"}'
read -r status total < <(feature /tickets/extraction ticket-tk-00042.json); note_status "$status"
echo "F4: status=$status total=${total}s corpo=$(cat "$BODY_FILE")"
check "F4 → 503 explícito" "$([ "$status" = 503 ] && echo 0 || echo 1)"

poll_until_done() { # location limite_s → imprime a linha do tempo; deixa o último código em $BODY_FILE.code
  local t0 code; t0=$(now)
  while :; do
    code=$(curl -s -o "$BODY_FILE" -w '%{http_code}' "$EDGE$1"); note_status "$code"
    echo "    +$(elapsed "$t0" "$(now)")s $code $(cat "$BODY_FILE")"
    echo "$code" > "$BODY_FILE.code"
    if [ "$code" != 200 ] || ! grep -qE '"state":"(pending|running)"' "$BODY_FILE"; then break; fi
    if python -c "import sys; sys.exit(0 if $(elapsed "$t0" "$(now)") > $2 else 1)"; then echo "    limite de $2 s"; break; fi
    sleep "${3:-1}"
  done
  echo "$(elapsed "$t0" "$(now)")" > "$BODY_FILE.t"
}

echo "## F3 com os dois providers inteiros em error_500 (limite 60 s para failed)"
reset_provider; set_failure '{"provider": "openai", "mode": "error_500"}'; set_failure '{"provider": "anthropic", "mode": "error_500"}'
curl -s -D "$BODY_FILE.h" -o "$BODY_FILE" -X POST "$EDGE/reports/topics" -H 'Content-Type: application/json' --data-binary "@$PAYLOADS/period-mes.json"
location=$(grep -i '^location' "$BODY_FILE.h" | tr -d '\r' | awk '{print $2}')
poll_until_done "$location" 60
grep -q '"state":"failed"' "$BODY_FILE" && grep -q '"reason"' "$BODY_FILE"; check "F3 chega a failed com motivo" $?
check "F3 failed em até 60 s" "$(python -c "import sys; sys.exit(0 if float('$(cat "$BODY_FILE.t")') <= 60 else 1)" && echo 0 || echo 1)"

echo "## F3 mês inteiro (2026-08-01 a 2026-08-31), modo normal"
docker compose restart app >/dev/null 2>&1; docker compose up -d --wait app >/dev/null 2>&1
reset_provider
t0=$(now)
code=$(curl -s -D "$BODY_FILE.h" -o "$BODY_FILE" -w '%{http_code}' -X POST "$EDGE/reports/topics" \
  -H 'Content-Type: application/json' --data-binary "@$PAYLOADS/period-mes.json"); accept=$(elapsed "$t0" "$(now)"); note_status "$code"
echo "pedido: status=$code em ${accept}s | $(grep -iE '^(location|retry-after)' "$BODY_FILE.h" | tr -d '\r' | tr '\n' ' ')| corpo=$(cat "$BODY_FILE")"
check "F3 aceita em até 1 s (202)" "$(python -c "import sys; sys.exit(0 if '$code' == '202' and float('$accept') <= 1 else 1)" && echo 0 || echo 1)"
location=$(grep -i '^location' "$BODY_FILE.h" | tr -d '\r' | awk '{print $2}')
poll_until_done "$location" 900 15 | awk 'NR % 4 == 1 || /303/'
result=$(curl -s -i "$EDGE$location" | grep -i '^location' | tr -d '\r' | awk '{print $2}')
code=$(curl -s -o "$BODY_FILE" -w '%{http_code}' "$EDGE$result"); note_status "$code"
total_tickets=$(python -c "import json; print(json.load(open('$BODY_FILE', encoding='utf-8'))['total_tickets'])")
topics_calls=$(curl -s "$PROVIDER/admin/calls?last=500" | python -c "import sys,json; print(sum(1 for c in json.load(sys.stdin) if c['task']=='topics' and c['status']==200))")
echo "resultado ($result): status=$code total_tickets=$total_tickets | chamadas topics 200 em /admin/calls: $topics_calls"
check "relatório do mês com total_tickets = 5000" "$([ "$total_tickets" = 5000 ] && echo 0 || echo 1)"
check "34 chamadas topics registradas em /admin/calls" "$([ "$topics_calls" = 34 ] && echo 0 || echo 1)"

echo "## Nenhum 504 da borda"
echo "status observados:$STATUSES"
echo "$STATUSES" | grep -qw 504; check "nenhuma resposta 504" "$([ $? -ne 0 ] && echo 0 || echo 1)"
rm -f "$BODY_FILE".h "$BODY_FILE".sse "$BODY_FILE".code "$BODY_FILE".t
finish
