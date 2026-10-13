#!/usr/bin/env bash
# F01, dor 1: o relatório do mês morre na borda (504) e o trabalho continua depois.
set -u
cd "$(dirname "$0")/../.."
E=docs/evidence/f01
count_topics() {
  curl -s "localhost:8090/admin/calls?last=200" | python -c "import sys,json;c=[x for x in json.load(sys.stdin) if x['task']=='topics'];print(len(c), sum(x['input_tokens'] or 0 for x in c), sum(x['output_tokens'] or 0 for x in c), sum(1 for x in c if x['duration_ms'] is None))"
}
curl -s -X POST localhost:8090/admin/reset >/dev/null
{
  echo "# Dor 1: relatório do mês ($(date -u +%FT%TZ))"
  echo "\$ curl -s -X POST localhost:8000/reports/topics -H 'Content-Type: application/json' --data-binary @scripts/diagnostics/payloads/period-mes.json"
  curl -s -X POST localhost:8000/reports/topics -H "Content-Type: application/json" \
    --data-binary @scripts/diagnostics/payloads/period-mes.json -w '\n--\nstatus=%{http_code} ttfb=%{time_starttransfer}s total=%{time_total}s\n'
  echo "# 504 recebido em $(date -u +%T). Chamadas topics em /admin/calls (qtd, input_tokens, output_tokens, em_andamento):"
} > $E/pain1-report.txt
for i in $(seq 0 24); do echo "$(date -u +%T) +$((i*15))s $(count_topics)"; sleep 15; done > $E/pain1-calls-after-504.txt
curl -s "localhost:8090/admin/calls?last=200" > $E/pain1-admin-calls.json
cat $E/pain1-report.txt $E/pain1-calls-after-504.txt
