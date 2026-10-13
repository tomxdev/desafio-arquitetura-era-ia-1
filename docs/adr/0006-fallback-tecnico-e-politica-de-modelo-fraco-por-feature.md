# 0006. Fallback técnico entre providers e política de modelo fraco por feature

- Status: aceita
- Data: 2026-10-13
- Nível: solução

## Contexto

Na v1, com um provider em `error_500`, as features presas a ele param (dor 3): F1/F4 com o `openai`, F2/F3 com o `anthropic`. Os modelos `large` dos dois providers são equivalentes (mesma saída para a mesma entrada: confirmado no diagnóstico nas quatro tarefas). Os `mini` são mais rápidos e baratos, mas piores, e o diagnóstico mediu onde ([resumo](../evidence/f01/models-compare/summary.md), amostra fixa de `data/tickets.jsonl`):

| Tarefa | Mini × large | Tempo large → mini |
|---|---|---|
| `classify` | idêntico em 40/40 tickets | 1,1 s → 0,4 s |
| `extract` | **diverge em 9/40**: em 4, devolve o número da **nota fiscal** como `order_number` (ex.: TK-00002, "nota fiscal 530720 … pedido #605065" → `#530720`), em formato válido, que passa pela validação da aplicação; em 6, perde o `product` | 1,1 s → 0,4 s |
| `suggest` | texto válido, mas com ~44% do tamanho (≈1.070 × 2.430 caracteres) | 16 s → 2,1 s |
| `topics` | idêntico num lote de 150 tickets (mesmos temas, contagens e exemplos) | 9,8 s → 2,7 s |

A pergunta não é "o gateway consegue fazer fallback?", e sim "uma resposta pior é melhor que nenhuma, para quem consome esta feature?".

## Opções consideradas

1. Sem fallback (como na v1).
2. Fallback técnico para o `large` equivalente do outro provider, em todas as capacidades; modelo fraco nunca.
3. Fallback técnico em todas + modelo fraco decidido feature a feature.
4. Modelo fraco direto, sem passar pelo outro `large`.

## Decisão

Opção 3, configurada no gateway (`router_settings.fallbacks` em `gateway/config.yaml`). Ordem por capacidade: **primário → fallback técnico (o `large` do outro provider) → modelo fraco, se a feature permitir**. Retry e timeout por destino estão no ADR 0009.

### F1 Classificar ticket: modelo fraco **sim** (`gpt-fake-mini`)
Cliente esperando a confirmação na tela; saída curta, de valores fixos. Na amostra, o `mini` classificou igual ao `large` em 40/40, e uma classificação imprecisa é corrigível depois pelo atendente. Falhar deixaria o cliente sem confirmação.

### F2 Sugerir resposta: modelo fraco **sim** (`claude-fake-mini`)
Quem consome é um atendente que **lê e edita** antes de enviar. A sugestão do `mini` é válida, só mais curta (~44%): um rascunho menor ainda poupa trabalho, e o humano revisa. Falhar deixaria o atendente sem nada.

### F3 Relatório de temas: modelo fraco **sim** (`claude-fake-mini`)
Painel interno, sem ninguém esperando. Na amostra, o `mini` gerou exatamente os mesmos temas e contagens do `large`. Como cada lote pode cair no `mini` sozinho, um relatório produzido sem nenhum `large` disponível sai com a qualidade observada nessa amostra. Aceitamos, porque a alternativa é o relatório inteiro falhar por causa de um lote.

### F4 Extrair dados do pedido: modelo fraco **não** (falha explícita)
Alimenta uma automação de troca e devolução **sem revisão humana**: um campo errado gera uma troca errada (frete, estoque, cliente). O `mini` errou 9/40, e o erro mais grave (nota fiscal no lugar do pedido) tem formato válido e **passa pela validação**, ou seja, seria executado em silêncio. Sem nenhum `large`, a F4 responde `503` com o motivo; a automação pode tentar de novo ou encaminhar para um humano.

## Consequências

- Com um provider inteiro fora, as quatro features continuam respondendo pelo `large` do outro provider, com a mesma saída (equivalência confirmada).
- Sem nenhum `large`, F1/F2/F3 respondem com qualidade menor (e mais barato); F4 falha explicitamente. A resposta via `mini` não é sinalizada no corpo (o contrato não muda); o `/admin/calls` e o log do gateway mostram qual modelo respondeu.
- O fallback aumenta a latência no pior caso (até 5 tentativas em F1/F2/F3; ver ADR 0009).

## Evidência

`bash scripts/verify/fallback.sh` ([saída](../evidence/f06/fallback.txt)): com o primário de cada capacidade em `error_500`, `/admin/calls` mostra 2 tentativas no primário seguidas do sucesso no `large` do outro provider (ex.: F1 `gpt-fake-large:500 gpt-fake-large:500 claude-fake-large:200`, 3,4 s). Com os dois `large` em `error_500`: F1 `200` via `gpt-fake-mini`, F2 e F3 `200` via `claude-fake-mini`, F4 `503 {"detail":"Capacidade helpdesk-extract indisponível: nenhum modelo disponível (gateway respondeu 500)"}` sem nenhuma chamada a modelo `mini`.
