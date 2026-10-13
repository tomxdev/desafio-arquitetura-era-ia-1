#!/usr/bin/env bash
# F01, dor 3: com um provider fora do ar ou travado, as features presas a ele param.
set -u
cd "$(dirname "$0")/../.."
E=docs/evidence/f01
P=scripts/diagnostics/payloads
W='status=%{http_code} total=%{time_total}s'
fail() { curl -s -X POST localhost:8090/admin/failures -H "Content-Type: application/json" -d "$1"; echo; }
hit() { # rota payload
  printf '%s -> ' "$1"
  curl -s -X POST "localhost:8000$1" -H "Content-Type: application/json" --data-binary "@$P/$2" -w " | $W\n" | tr -d '\n' | sed 's/ | status/\n   status/'; echo
}
calls() { curl -s "localhost:8090/admin/calls?last=$1" | python -c "import sys,json;[print('  ',c['ts'][11:23],c['provider'],c['model'],c['task'],'status=',c['status'],'dur_ms=',c['duration_ms']) for c in reversed(json.load(sys.stdin))]"; }

{
echo "# Dor 3a: provider openai em error_500 ($(date -u +%FT%TZ))"
curl -s -X POST localhost:8090/admin/reset >/dev/null
echo "\$ POST /admin/failures {\"provider\":\"openai\",\"mode\":\"error_500\"}"; fail '{"provider":"openai","mode":"error_500"}'
hit /tickets/classification ticket-tk-00042.json
hit /tickets/extraction ticket-tk-00042.json
hit /tickets/reply-suggestion ticket-tk-00042.json | cut -c1-200
hit /reports/topics period-1-dia.json | cut -c1-200
echo "/admin/calls (do mais antigo para o mais recente):"; calls 20

echo; echo "# Dor 3b: provider anthropic em error_500"
curl -s -X POST localhost:8090/admin/reset >/dev/null
echo "\$ POST /admin/failures {\"provider\":\"anthropic\",\"mode\":\"error_500\"}"; fail '{"provider":"anthropic","mode":"error_500"}'
hit /tickets/reply-suggestion ticket-tk-00042.json
hit /reports/topics period-1-dia.json
hit /tickets/classification ticket-tk-00042.json
echo "/admin/calls:"; calls 20

echo; echo "# Dor 3c: provider openai em timeout (segura a conexão por 300 s)"
curl -s -X POST localhost:8090/admin/reset >/dev/null
echo "\$ POST /admin/failures {\"provider\":\"openai\",\"mode\":\"timeout\"}"; fail '{"provider":"openai","mode":"timeout"}'
hit /tickets/classification ticket-tk-00042.json
echo "/admin/calls logo após a resposta da borda:"; calls 5
echo "# Esperado pelo SDK: read timeout de 600 s e 2 retries; a borda desiste aos 30 s, mas a thread do app continua presa."
} 2>&1 | tee $E/pain3-provider-down.txt
curl -s -X POST localhost:8090/admin/reset >/dev/null
