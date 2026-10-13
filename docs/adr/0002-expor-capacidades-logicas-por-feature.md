# 0002. Expor capacidades lógicas por feature e mapear os modelos físicos só no gateway

- Status: aceita
- Data: 2026-10-13
- Nível: software

## Contexto

Na v1 o nome físico do modelo é constante no código (`config.py:10-13`), e é por isso que trocar de modelo exige deploy (dor 4). O requisito 5 pede que a aplicação conheça só nomes lógicos, e que nenhum `gpt-fake-*`/`claude-fake-*` apareça em `app/`. As quatro features têm necessidades diferentes de produto: a extração alimenta uma automação sem revisão humana, e o diagnóstico mostrou que o `mini` erra 9/40 extrações (4 com a nota fiscal no lugar do pedido), enquanto em `classify` e `topics` ele foi idêntico ao `large` na amostra.

## Opções consideradas

1. Uma capacidade por tamanho de modelo (`chat-large`, `chat-mini`), escolhida pela feature.
2. Uma capacidade por feature (`helpdesk-classify`, `helpdesk-suggest`, `helpdesk-topics`, `helpdesk-extract`).
3. Uma capacidade única (`helpdesk`), com o roteamento decidido por metadados.

## Decisão

Opção 2. O nome lógico é o contrato entre a aplicação e a infraestrutura: cada feature declara a sua (`CAPABILITY` no módulo da feature) e pede à porta `ports.LLMGateway`; o mapeamento para o modelo físico existe **só** em `gateway/config.yaml`. A granularidade por feature é a que permite políticas diferentes por feature (modelo primário, fallback técnico, fallback com modelo fraco, timeout) sem tocar na aplicação. A opção 1 devolveria à feature a decisão do modelo (o problema da v1, com outro nome); a 3 esconderia a decisão de produto em regras de roteamento.

Mapeamento na `v2-decoupled` (comportamento idêntico à v1: um `large` por capacidade, no mesmo provider da v1):

| Capacidade | Feature | Modelo físico |
|---|---|---|
| `helpdesk-classify` | F1 | `openai/gpt-fake-large` |
| `helpdesk-suggest` | F2 | `anthropic/claude-fake-large` |
| `helpdesk-topics` | F3 | `anthropic/claude-fake-large` |
| `helpdesk-extract` | F4 | `openai/gpt-fake-large` |

## Consequências

- Trocar o modelo físico de uma feature não afeta as outras e não toca no código.
- Os quatro nomes viram vocabulário compartilhado: renomear uma capacidade exige mudar o gateway e a feature juntos.
- Fallback técnico e política de modelo fraco ficam por capacidade (ADR de fallback, F06).

## Evidência

```bash
grep -rE "gpt-fake|claude-fake" app/          # vazio
grep -rn "CAPABILITY =" app/helpdesk          # um nome lógico por feature
grep -n "model_name" gateway/config.yaml
```

Reexecutado na F08 ([saída](../evidence/f08/adr-evidence.txt)): um `CAPABILITY` por feature e 11 `model_name` no gateway (4 capacidades, 4 `-fallback`, 3 `-weak`).
