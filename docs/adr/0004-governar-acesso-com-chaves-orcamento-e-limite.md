# 0004. Governar o acesso aos modelos com chaves virtuais, orçamento e limite de requisições no gateway

- Status: aceita
- Data: 2026-10-13
- Nível: solução

## Contexto

Na v1, o gasto com IA não tinha dono nem limite: no diagnóstico, um único pedido do relatório do mês consumiu US$ 0,85, dos quais 88% depois do 504 da borda (dor 1). O requisito 5 pede pelo menos uma chave com orçamento e uma com limite de requisições, e que a requisição fora do limite seja recusada **pelo gateway, antes de chegar ao provider**. A pista do enunciado avisa que, sem preço declarado, o gateway calcula custo zero e nenhum orçamento estoura.

## Opções consideradas

1. Contar gasto e requisições na aplicação.
2. Usar as chaves virtuais do gateway (LiteLLM), com orçamento e limite por chave, e os preços declarados por modelo.
3. Limitar só na borda (nginx), por IP.

## Decisão

Opção 2. O gateway é o único ponto por onde toda chamada passa (ADR 0001) e já conhece o modelo físico e os tokens de cada resposta, então é onde o custo pode ser calculado e o limite aplicado antes de chamar o provider. A opção 1 duplicaria a lógica em cada serviço que usasse IA; a 3 não sabe nada de tokens nem de custo.

- **Preços:** `model_info.input_cost_per_token`/`output_cost_per_token` de cada deployment em `gateway/config.yaml`, copiados da tabela do `provider-fake/README.md` (ex.: `gpt-fake-large` US$ 2,50/US$ 10,00 por 1M tokens).
- **Chaves** (criadas na subida por `gateway/seed_keys.py`, sem passo manual; valores fixos de laboratório no `.env.example`):

  | Chave (alias) | Quem usa | Modelos | Orçamento | Limite |
  |---|---|---|---|---|
  | `helpdesk-app` | serviço `app` | as 4 capacidades | US$ 100 a cada 30 dias (ADR 0005) | 600 req/min |
  | `demo-budget` | roteiro de governança | `helpdesk-classify` | US$ 0,0001 (uma classificação custa ~US$ 0,00013) | — |
  | `demo-rpm` | roteiro de governança | `helpdesk-classify` | — | 2 req/min |

- **Rotação:** se o valor de uma chave muda no `.env`, o seeder revoga a chave antiga com o mesmo alias antes de criar a nova (`/key/delete` por `key_aliases`).

## Consequências

- Uma requisição sem orçamento ou acima do limite recebe `429` do gateway (`budget_exceeded` / `Rate limit exceeded`) e **não** chega ao provider; para o app, isso vira `503` com o motivo (`CapabilityUnavailable`, ADR 0009).
- O orçamento é checado **antes** da chamada com o gasto acumulado até a chamada anterior: a requisição que cruza o teto ainda passa (no roteiro, a 1ª gasta US$ 0,00013 > US$ 0,0001) e só as seguintes são recusadas.
- Mudar o orçamento ou o limite de uma chave existente exige recriá-la (trocar o valor da chave ou `docker compose down -v`); o seeder não altera chaves já criadas.
- O preço dos modelos passa a ser configuração versionada: se o provider mudar o preço, o `config.yaml` precisa acompanhar.

## Evidência

`bash scripts/verify/governance.sh` ([saída](../evidence/f06/governance.txt)): a 1ª requisição com `demo-budget` passa (`/admin/calls` 0 → 1) e a seguinte é recusada com `429 budget_exceeded` (1 → 1); com `demo-rpm`, a 1ª e a 2ª passam (1 → 2 → 3) e a 3ª no mesmo minuto é recusada com `429` (3 → 3). Rotação: [saída](../evidence/f06/key-rotation.txt).

Reexecutado na F08: [saída](../evidence/f08/governance.txt), mesmo resultado (`RESULTADO: OK`).
