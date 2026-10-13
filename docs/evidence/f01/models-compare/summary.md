# Comparação large × mini no provider simulado (F01)

Amostra: os 40 primeiros tickets de `data/tickets.jsonl` (classify/extract), 5 (suggest) e um lote de 150 (topics). Referência: `gpt-fake-large`. Gerado por `scripts/diagnostics/compare_models.py`.

## classify

| modelo | tickets divergentes | category | priority | s/chamada |
|---|---|---|---|---|
| gpt-fake-large | referência | — | — | 1.12 |
| claude-fake-large | 0/40 | 0 | 0 | 1.11 |
| gpt-fake-mini | 0/40 | 0 | 0 | 0.4 |
| claude-fake-mini | 0/40 | 0 | 0 | 0.39 |

## extract

| modelo | tickets divergentes | order_number | product | s/chamada |
|---|---|---|---|---|
| gpt-fake-large | referência | — | — | 1.09 |
| claude-fake-large | 0/40 | 0 | 0 | 1.08 |
| gpt-fake-mini | 9/40 | 4 | 6 | 0.38 |
| claude-fake-mini | 9/40 | 4 | 6 | 0.38 |

### extract: `order_number` contra o número citado no texto

Tickets da amostra que citam `#NNNNNN` no texto: 9.

| modelo | order_number diferente do citado no texto |
|---|---|
| gpt-fake-large | 0/9 |
| claude-fake-large | 0/9 |
| gpt-fake-mini | 2/9 |
| claude-fake-mini | 2/9 |

## suggest

| ticket | gpt-fake-large chars (s) | claude-fake-large chars (s) | gpt-fake-mini chars (s) | claude-fake-mini chars (s) | claude-large == gpt-large | minis == gpt-large |
|---|---|---|---|---|---|---|
| TK-00001 | 2402 (15.83) | 2402 (15.83) | 1066 (2.09) | 1066 (2.09) | True | False/False |
| TK-00002 | 2451 (16.13) | 2451 (16.13) | 1099 (2.14) | 1099 (2.14) | True | False/False |
| TK-00003 | 2444 (16.08) | 2444 (16.08) | 1072 (2.09) | 1072 (2.09) | True | False/False |
| TK-00004 | 2457 (16.18) | 2457 (16.18) | 1060 (2.07) | 1060 (2.07) | True | False/False |
| TK-00005 | 2424 (15.97) | 2424 (15.95) | 1066 (2.09) | 1066 (2.09) | True | False/False |

## topics (um lote)

| modelo | temas | soma dos counts | s |
|---|---|---|---|
| gpt-fake-large | 15 | 150 | 9.83 |
| claude-fake-large | 15 | 150 | 9.83 |
| gpt-fake-mini | 15 | 150 | 2.72 |
| claude-fake-mini | 15 | 150 | 2.72 |

Saída do topics idêntica entre os dois large: True.

## Leitura (F01)

- **classify:** os dois `mini` deram exatamente a mesma `category`/`priority` do `large` nos 40 tickets.
- **extract:** os `mini` divergem em 9/40 tickets. Em 4 deles, o `mini` devolve o número da **nota fiscal** como `order_number` (ex.: TK-00002 cita "nota fiscal 530720" e "pedido #605065": large `#605065`, mini `#530720`; idem TK-00015, TK-00032 e TK-00036). Esse valor tem o formato válido `#NNNNNN` e **passa** pela validação de `app/helpdesk/extraction.py:16`, ou seja, o erro é silencioso. Em 6 tickets (TK-00007, 00030, 00031, 00033, 00036, 00040; o TK-00036 também com o pedido errado), o `mini` perde o `product` (`null` no lugar de "notebook 14 polegadas", "edredom casal" etc.).
- **suggest:** os `mini` geram texto válido, mas com ~44% do tamanho (≈1.070 vs. ≈2.430 caracteres) e diferente do `large`; os `large` são idênticos entre si e levam ≈16 s sem streaming.
- **topics:** no lote de 150 tickets, a saída dos `mini` é **idêntica** à dos `large` (mesmos temas, counts e exemplos), em 2,7 s vs. 9,8 s.
- Os dois `large` são idênticos entre si nas quatro tarefas (confirma a equivalência declarada).
