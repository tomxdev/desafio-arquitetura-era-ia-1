# Plano de refatoração: de `v1-coupled` a `v2-decoupled`

> Requisito 4. Refatoração é mudança de estrutura **sem** mudança de comportamento: o juiz do comportamento é a suíte de caracterização (`tests/characterization/`, idêntica entre as tags), e o juiz da estrutura é a métrica (`metrics/coupling.py`, régua do requisito 3, [ADR 0008](adr/0008-medir-acoplamento-pela-regua-fixa.md)).

## 1. Ponto de partida (medido)

`metrics/results/v1-coupled.csv`:

| component | ca | ce | i | a | d | leitura |
|---|---|---|---|---|---|---|
| classification | 1 | 3 | 0.75 | 0.00 | 0.25 | depende de `llm` e `config` concretos |
| config | 6 | 0 | 0.00 | 0.00 | **1.00** | **zona de dor**: modelos físicos, chaves e URLs dos providers; todo mundo importa |
| extraction | 1 | 3 | 0.75 | 0.00 | 0.25 | idem `classification` |
| llm | 4 | 1 | 0.20 | 0.00 | **0.80** | **zona de dor**: dois SDKs, sem timeout/retry; as 4 features chamam direto |
| main | 0 | 5 | 1.00 | 0.00 | 0.00 | rotas; não monta nada (as features buscam suas dependências sozinhas) |
| report | 1 | 4 | 0.80 | 0.00 | 0.20 | depende de `llm`, `config`, `tickets` |
| schemas | 5 | 0 | 0.00 | 0.00 | **1.00** | **zona de dor** pela fórmula; tipos de valor do contrato HTTP |
| suggestion | 1 | 3 | 0.75 | 0.00 | 0.25 | idem `classification` |
| tickets | 1 | 1 | 0.50 | 0.00 | 0.50 | leitura de `/data/tickets.jsonl`; caminho vem de `config` |

O diagnóstico da v1 (README) liga as dores a esses mesmos pontos: o nome do modelo e o provider em `config`, a chamada sem timeout/fallback em `llm`, e cada feature presa ao seu provider.

## 2. Componentes-alvo e estratégia (versão inicial)

| Alvo | Problema | Estratégia | Resultado esperado |
|---|---|---|---|
| `llm` | concreto (A 0) e muito usado (Ca 4): o detalhe mais volátil (provider, SDK, formato) é do que as features dependem | **Inverter a dependência**: uma porta `ports.LLMGateway` (`typing.Protocol`) que as features usam; a implementação concreta fica num único componente, montado pelo ponto de composição (`main`) | `ports` com A 1, I 0 (na Main Sequence); o componente concreto deixa de ser importado pelas features |
| features (`classification`, `suggestion`, `extraction`, `report`) | buscam `llm` e `config` sozinhas (import de módulo global) | **Compor em vez de buscar**: a feature recebe o gateway (injeção pelo ponto de composição) e pede uma **capacidade lógica**, sem saber provider nem modelo | Ce só para `ports` e `schemas` |
| `config` | Ca 6: nomes físicos e chaves espalhados | **Reduzir Ca**: nomes físicos saem do app (vão para o gateway na F05); o que sobra (endereço e chave do gateway, timeouts) é lido por quem monta a aplicação | Ca cai a cada feature migrada |
| `tickets` | caminho do arquivo vem de `config` | receber o caminho de quem monta (sem `config`) | Ce 0 |
| `schemas` | D 1 pela fórmula | **não mexer**: tipos do contrato, fixados pela suíte | candidato a "estável por natureza" (ADR 0008) |

## 3. Critério de pronto

1. `python -m pytest tests/characterization -q` passa e `git diff v1-coupled -- tests/characterization/` é vazio.
2. Nenhum componente na zona de dor (A < 0,5, I < 0,5 e D ≥ 0,5), exceto os declarados no ADR 0008 como estáveis por natureza (nunca o componente que chama o gateway nem as features).
3. O código que chama o modelo (SDK/HTTP) fica num único componente, e só o ponto de composição o importa (`grep` nas features vazio).
4. A partir da F05: nenhum nome físico (`gpt-fake-*`, `claude-fake-*`) nem chave de provider em `app/`.

## 4. Piloto

*A executar: um único componente (`classification`), medição antes e depois.*

## 5. Revisões do plano

*A registrar depois do piloto.*

## 6. Handoff para o agente de IA

*A registrar (protocolo na seção 6 após o piloto; execução na F05).*
