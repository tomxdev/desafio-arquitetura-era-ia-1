$ for s in ...; do grep -q "^## $s" README.md || echo "FALTA: $s"; done
ok: Visão geral
ok: Diagnóstico da v1
ok: Como rodar
ok: Métrica
ok: Tabela de capacidades
ok: Tabela de fallback
ok: Fluxos
ok: Troca de modelo
ok: Roteiro de governança
ok: Mapa de decisões
$ grep -ci "em construção" README.md
0
