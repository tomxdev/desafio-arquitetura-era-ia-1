#!/usr/bin/env bash
# Revalidação da versão final contra a main, num clone limpo, seguindo o README.
# Qualquer passo que falhe interrompe a execução com código diferente de zero; a saída gravada
# em run.txt só existe se todos os passos chegaram ao fim.
set -euo pipefail
W=/c/dev/f09-main
cd "$W" || exit 1
rm -rf fresh
echo "# Clone limpo da main ($(date -u +%FT%TZ))"
git clone -q --branch main https://github.com/tomxdev/desafio-arquitetura-era-ia-1.git fresh
cd fresh || exit 1
echo "commit: $(git log --oneline -1)"
echo "CRLF no checkout: $(git ls-files --eol | { grep -c w/crlf || true; })"
echo '$ cp .env.example .env && docker compose up -d --build --wait'
cp .env.example .env && docker compose up -d --build --wait 2>&1 | tail -1
echo "\$ curl localhost:8000/health → $(curl -s -o /dev/null -w '%{http_code}' localhost:8000/health)"
python -m venv .venv && source .venv/Scripts/activate
pip install -q -r tests/requirements.txt -r metrics/requirements.txt
echo; echo '$ python -m pytest -q'; python -m pytest -q 2>&1 | tail -1
for v in v1-coupled v2-decoupled; do
  git worktree add -q ../wt-$v $v
  python metrics/coupling.py ../wt-$v/app/helpdesk --name $v >/dev/null
  git worktree remove --force ../wt-$v
done
python metrics/coupling.py app/helpdesk --name main >/dev/null
for v in v1-coupled v2-decoupled main; do
  git diff --quiet -- metrics/results/$v.csv || { echo "$v.csv DIFERENTE"; exit 1; }
  echo "$v.csv reproduzido"
done
for s in governance fallback model_swap flows; do
  t0=$(date +%s); rc=0; bash scripts/verify/$s.sh > "$W/$s.txt" 2>&1 || rc=$?
  echo "\$ bash scripts/verify/$s.sh → exit=$rc $(grep RESULTADO "$W/$s.txt" | tail -1) ($(( $(date +%s)-t0 )) s)"
  [ "$rc" -eq 0 ] || exit "$rc"
done
git fetch -q https://github.com/devfullcycle/desafio-arquitetura-era-ia-1.git main
echo "protegidas vs base: $(git diff --stat FETCH_HEAD HEAD -- provider-fake edge data | wc -l) linhas de diff"
deactivate; docker compose down -v >/dev/null 2>&1
echo "# fim ($(date -u +%FT%TZ))"
