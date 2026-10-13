#!/usr/bin/env bash
# F01, dor 2: a sugestão de resposta não mostra nada até o texto inteiro ficar pronto.
set -u
cd "$(dirname "$0")/../.."
E=docs/evidence/f01
curl -s -X POST localhost:8090/admin/reset >/dev/null
{
  echo "# Dor 2: sugestão de resposta ($(date -u +%FT%TZ))"
  echo "\$ curl -sN -X POST localhost:8000/tickets/reply-suggestion -H 'Content-Type: application/json' --data-binary @scripts/diagnostics/payloads/ticket-tk-00042.json"
  curl -sN -o /dev/null -X POST localhost:8000/tickets/reply-suggestion -H "Content-Type: application/json" \
    --data-binary @scripts/diagnostics/payloads/ticket-tk-00042.json \
    -w 'status=%{http_code} content_type=%{content_type} ttfb=%{time_starttransfer}s total=%{time_total}s bytes=%{size_download}\n'
  echo "\$ curl -s 'localhost:8090/admin/calls?last=1'"
  curl -s "localhost:8090/admin/calls?last=1"; echo
} | tee $E/pain2-suggestion.txt
