#!/usr/bin/env bash
# Sobe o LiteLLM Proxy e semeia as chaves virtuais sem passo manual.
# O healthcheck do serviço só passa depois que as chaves existem (/tmp/keys-ready).
set -euo pipefail

rm -f /tmp/keys-ready
litellm --config /etc/litellm/config.yaml --port 4000 &
pid=$!
trap 'kill -TERM "$pid" 2>/dev/null' TERM INT

python /etc/litellm/seed_keys.py && touch /tmp/keys-ready

wait "$pid"
