#!/usr/bin/env bash
# F01: exercita F1–F4 pela borda (localhost:8000), em modo normal, e grava corpo, tempos e /admin/calls.
# Os corpos vêm de arquivos (--data-binary @arquivo): no Windows, acentos passados como argumento
# do curl chegam corrompidos e a aplicação responde 400.
set -u
cd "$(dirname "$0")/../.."
P=scripts/diagnostics/payloads
E=docs/evidence/f01/features
mkdir -p "$E"
W='\n--\nstatus=%{http_code} ttfb=%{time_starttransfer}s total=%{time_total}s\n'

run() { # nome rota payload
  curl -s -X POST localhost:8090/admin/reset >/dev/null
  {
    echo "\$ curl -s -X POST localhost:8000$2 -H 'Content-Type: application/json' --data-binary @$P/$3"
    echo "# corpo: $(cat "$P/$3")"; echo
    curl -s -X POST "localhost:8000$2" -H "Content-Type: application/json" --data-binary "@$P/$3" -w "$W"
    echo; echo "\$ curl -s 'localhost:8090/admin/calls?last=5'"
    curl -s "localhost:8090/admin/calls?last=5"; echo
  } > "$E/$1.txt"
  grep -E "^status=" "$E/$1.txt" | sed "s/^/$1 /"
}

run f1-classification /tickets/classification ticket-tk-00042.json
run f2-reply-suggestion /tickets/reply-suggestion ticket-tk-00042.json
run f4-extraction /tickets/extraction ticket-tk-00042.json
run f4-extraction-sem-pedido /tickets/extraction ticket-sem-pedido.json
run f3-topics-1-dia /reports/topics period-1-dia.json
