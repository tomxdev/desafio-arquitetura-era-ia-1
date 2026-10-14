#!/usr/bin/env bash
# Troca de modelo só por configuração do gateway (README, "Troca de modelo"):
# muda helpdesk-classify de openai/gpt-fake-large para openai/gpt-fake-mini em gateway/config.yaml,
# reinicia SÓ o gateway, confere o novo modelo em /admin/calls e que o app não foi reiniciado; depois desfaz.
source "$(dirname "$0")/_lib.sh"
CONFIG=gateway/config.yaml

if ! git diff --quiet -- "$CONFIG"; then echo "$CONFIG tem alterações locais; faça commit ou stash antes." >&2; exit 1; fi
quiesce
app_started() { docker inspect -f '{{.State.StartedAt}}' "$(docker compose ps -q app)"; }
wait_gateway() { docker compose up -d --wait gateway >/dev/null 2>&1; }
swap() { # de para (só a 1ª linha de helpdesk-classify)
  python - "$1" "$2" <<'EOF'
import sys
path = "gateway/config.yaml"
text = open(path, encoding="utf-8").read()
marker = "- model_name: helpdesk-classify\n    litellm_params: {model: " + sys.argv[1]
assert text.count(marker) == 1, "bloco helpdesk-classify não encontrado"
open(path, "w", encoding="utf-8", newline="\n").write(text.replace(marker, marker.replace(sys.argv[1], sys.argv[2])))
EOF
}

echo "# Troca de modelo ($(date -u +%FT%TZ))"
reset_provider
before_start=$(app_started)
read -r status _ < <(feature /tickets/classification ticket-tk-00042.json)
echo "antes: F1 status=$status | /admin/calls: $(call_models 1) | app iniciado em $before_start"

echo "## 1) editar $CONFIG (helpdesk-classify: openai/gpt-fake-large → openai/gpt-fake-mini)"
swap openai/gpt-fake-large openai/gpt-fake-mini
git diff --unified=0 -- "$CONFIG" | grep -E '^[-+] ' | sed 's/^/    /'
echo "## 2) docker compose restart gateway"
docker compose restart gateway >/dev/null 2>&1; wait_gateway
reset_provider
read -r status _ < <(feature /tickets/classification ticket-tk-00042.json)
after_start=$(app_started)
echo "depois: F1 status=$status | /admin/calls: $(call_models 1) | app iniciado em $after_start"
check "F1 responde 200" "$([ "$status" = 200 ] && echo 0 || echo 1)"
check "próxima chamada usa gpt-fake-mini" "$([ "$(call_models 1)" = "gpt-fake-mini:200" ] && echo 0 || echo 1)"
check "app NÃO foi reiniciado (StartedAt igual)" "$([ "$before_start" = "$after_start" ] && echo 0 || echo 1)"

echo "## 3) desfazer (git checkout -- $CONFIG + restart do gateway)"
git checkout -- "$CONFIG"
docker compose restart gateway >/dev/null 2>&1; wait_gateway
reset_provider
read -r status _ < <(feature /tickets/classification ticket-tk-00042.json)
check "de volta a gpt-fake-large" "$([ "$(call_models 1)" = "gpt-fake-large:200" ] && echo 0 || echo 1)"

finish
