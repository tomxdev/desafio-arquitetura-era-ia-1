# Reprodução: pytest completo e, logo depois, os roteiros (ordem do README), com quiesce (2026-10-14T03:23:04Z), commit-base 5290ebf + mudanças da feature/09-validacao
$ python -m pytest -q
25 passed, 1 skipped in 75.80s (0:01:15)
$ bash scripts/verify/governance.sh → exit=0 RESULTADO: OK (88 s)
$ bash scripts/verify/fallback.sh → exit=0 RESULTADO: OK (91 s)
$ bash scripts/verify/model_swap.sh → exit=0 RESULTADO: OK (47 s)
$ bash scripts/verify/flows.sh → exit=0 RESULTADO: OK (421 s)
