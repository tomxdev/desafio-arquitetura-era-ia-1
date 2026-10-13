# 0005. Limitar o gasto mensal do helpdesk com IA e os providers aceitos pela empresa

- Status: aceita
- Data: 2026-10-13
- Nível: corporativa

## Contexto

"Três meses depois, a conta chegou": o helpdesk passou a gastar com IA sem que ninguém tivesse decidido quanto ele podia gastar nem com quem. As features escolheram provider "porque funcionou melhor no teste", e na última instabilidade de um provider metade do atendimento parou. São duas perguntas de negócio, não de código: quanto a empresa aceita pagar por mês por este uso de IA, e de quais fornecedores ela aceita depender.

Custo esperado por mês, com os preços do provider e o consumo medido no diagnóstico, para 5.000 tickets/mês (o volume de agosto):

| Uso | Conta | US$/mês |
|---|---|---|
| F1 + F4 (1 classificação e 1 extração por ticket) | 2 × 5.000 × US$ 0,000158 | 1,57 |
| F2 (1 sugestão por ticket) | 5.000 × US$ 0,00915 | 45,74 |
| F3 (relatório do mês, ~4 execuções) | 4 × US$ 0,85 | 3,40 |
| **Total esperado** | | **~50,71** |

## Opções consideradas

1. Sem teto: pagar o que vier e olhar a fatura no fim do mês.
2. Teto mensal por aplicação, aplicado tecnicamente no gateway, com margem sobre o esperado.
3. Teto por feature.

## Decisão

- **Teto de gasto:** **US$ 100 a cada 30 dias** para o helpdesk (≈ 2× o esperado: absorve picos e fallbacks para o modelo mais caro do outro provider, mas impede que um defeito, como o da dor 1, multiplique a conta sem ninguém perceber). Aplicado como `max_budget` + `budget_duration: 30d` da chave `helpdesk-app` (ADR 0004). Teto por feature (opção 3) foi descartado por ora: exige uma chave por feature e uma decisão de prioridade entre elas que o negócio ainda não tomou.
- **Providers aceitos:** apenas os dois providers já contratados (`openai` e `anthropic`), sempre **por trás do gateway da empresa**; nenhum serviço chama provider direto, e nenhuma credencial de provider fica fora do gateway. Toda capacidade precisa ter um destino equivalente nos **dois** providers, para que a queda de um não pare o atendimento (ADR 0006).

## Consequências

- Ao atingir o teto, o helpdesk passa a receber `503` explícito nas features de IA até a janela renovar ou o teto ser revisto: é uma decisão consciente de parar de gastar, não uma falha silenciosa.
- Revisar o teto é uma decisão de negócio (este ADR), executada como configuração (recriar a chave com o novo valor).
- Incluir um terceiro provider exige revisar este ADR.

## Evidência

```bash
curl -s "localhost:4000/key/info?key=sk-helpdesk-app-0001" -H "Authorization: Bearer sk-litellm-master-0001"
# → "max_budget": 100.0, "budget_duration": "30d", "rpm_limit": 600
grep -c "model: openai/\|model: anthropic/" gateway/config.yaml   # só os dois providers aceitos
```

Reexecutado na F08 ([saída](../evidence/f08/adr-evidence.txt)): `max_budget` 100.0, `budget_duration` 30d, `rpm_limit` 600; os 11 deployments são `openai/*` ou `anthropic/*` e nenhum outro.
