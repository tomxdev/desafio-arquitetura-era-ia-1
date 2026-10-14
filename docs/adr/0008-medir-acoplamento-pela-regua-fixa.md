# 0008. Medir o acoplamento pela régua fixa e declarar as exceções estáveis por natureza

- Status: aceita
- Data: 2026-10-13
- Nível: software

## Contexto

Precisamos de um critério de pronto observável para a refatoração (requisito 3, módulo 02): cada componente de `app/helpdesk/` vira um ponto no gráfico A × I, e a distância à Main Sequence (D) mostra onde o acoplamento dói. A régua é fixa pelo enunciado, para que as medições de `v1-coupled`, `v2-decoupled` e `main` sejam comparáveis entre si e com a recalculada pelo avaliador.

Medição da `v1-coupled` (`metrics/results/v1-coupled.csv`): `config` (Ca 6, D 1,00), `llm` (Ca 4, I 0,20, D 0,80) e `schemas` (Ca 5, D 1,00) estão na zona de dor; as quatro features e `main` estão perto da Main Sequence só porque são instáveis (I ≥ 0,75) e não há nenhuma abstração (A = 0 em todo o pacote).

## Opções consideradas

1. Usar uma ferramenta pronta (ex.: pydeps, import-linter) e adaptar a saída.
2. Escrever um script próprio sobre o `ast` da biblioteca padrão, implementando a régua literalmente.

## Decisão

Opção 2: `metrics/coupling.py`. As ferramentas prontas resolvem imports e contam classes com regras próprias (pacotes como nós, sem contar `Protocol`/`ABC` como abstração), o que mudaria a régua. Com o script, a régua está no código e nos testes (`metrics/tests/test_coupling.py`, incluindo o oráculo calculado à mão para a v1).

Interpretações onde a régua não é explícita, fixadas para as três medições:

- O pacote raiz é a pasta medida (`helpdesk`): `import helpdesk.x` e `from helpdesk import x` resolvem para o componente `x`.
- `from <pacote> import nome` depende de `<pacote>.nome` se ele é um componente; senão, de `<pacote>`. Imports que resolvem para um `__init__` não contam.
- Todo import do módulo conta (inclusive dentro de funções e em `if TYPE_CHECKING:`), uma vez por componente; autoimport não conta.
- Todas as classes do módulo contam, inclusive aninhadas. Abstrata é a que tem `Protocol` ou `ABC` entre as **bases diretas** (`typing.Protocol`, `Protocol[T]`, `abc.ABC`); `metaclass=ABCMeta` e herança indireta não contam.
- Arredondamento "meio para cima" para 2 casas sobre o valor exato (frações), com D calculado antes de arredondar.

## Consequências

- A medição é determinística e reproduzível: o script da `main` sobre um checkout da `v1-coupled` gera o CSV versionado byte a byte (`docs/evidence/f03/reproducibility.txt`).
- A métrica aponta onde olhar; não justifica sozinha uma mudança de estrutura (nenhum import "para sair da zona").
- Componentes concretos que quase nunca mudam caem na zona de dor pela fórmula. Para esses, a exceção é declarada aqui, com justificativa; **não** podem ser exceção o componente que chama o gateway (`adapters.gateway`) nem os componentes das features, porque são exatamente o que muda quando o modelo, o provider ou a regra de negócio muda.

### Exceção estável por natureza: `schemas`

`schemas` (Ca 6, Ce 0, I 0,00, A 0,00, D 1,00 na `main`) é a única entrada na zona de dor da `main` e é aceita como exceção:

- São tipos de valor (`BaseModel` do pydantic) do contrato HTTP: entrada e saída de F1–F4. Não têm comportamento nem dependências internas (Ce 0).
- Mudam só quando o contrato muda, e o contrato é congelado pela suíte de caracterização (goldens da `v1-coupled`, inalterados até a `main`). Mudar `schemas` é, por definição, uma mudança de contrato para os clientes, não um detalhe de implementação.
- Tirá-lo da zona exigiria abstrair tipos de dados (um `Protocol` por DTO) ou espalhá-los pelas features; as duas opções aumentam o acoplamento real sem reduzir o risco de mudança.

### Leitura das três medições

| Componente | v1-coupled | v2-decoupled | main | Leitura |
|---|---|---|---|---|
| `config` | **zona de dor** (Ca 6, D 1,00) | — | — | dissolvido: nomes físicos e chaves foram para o gateway; o resto é lido em `main` |
| `llm` | **zona de dor** (Ca 4, I 0,20, D 0,80) | — | — | substituído pela porta `ports.LLMGateway` e pelo adaptador `adapters.gateway` |
| `ports` | — | A 1,00, I 0,00, D 0,00 | A 0,67, I 0,00, D 0,33 | abstração estável (Ca 6 → 8); na `main` também guarda a exceção `CapabilityUnavailable`, contrato de erro entre adaptador, features e `main` |
| `adapters.gateway` | — | I 0,50, D 0,50 | I 0,50, D 0,50 | único cliente do modelo, importado só por `main`; fora da zona |
| features (`classification`, `extraction`, `suggestion`, `report`) | I 0,75–0,80, D 0,20–0,25 | I 0,67, D 0,33 | I 0,67, D 0,33 | dependem só de `ports` e `schemas` |
| `report_jobs` | — | — | I 0,75, D 0,25 | execução assíncrona da F3 (ADR 0007), concreta e instável |
| `main` | I 1,00 | I 1,00 (Ce 7) | I 1,00 (Ce 8) | ponto de composição: o único que conhece as implementações |
| `tickets` | I 0,50, D 0,50 | I 0,50, D 0,50 | I 0,50, D 0,50 | implementa `ports.TicketSource`; na borda da zona, sem estar nela (I não é < 0,5) |
| `schemas` | zona de dor (D 1,00) | zona de dor (D 1,00) | zona de dor (D 1,00) | exceção estável por natureza (acima) |

"Zona de dor" é A < 0,5, I < 0,5 e D ≥ 0,5. Da `v1-coupled` para a `main`, os dois componentes voláteis da zona (`config`, `llm`) saíram, e o que sobrou nela é só a exceção declarada.

## Evidência

```bash
python -m pytest metrics/tests -q
git worktree add ../v1 v1-coupled && python metrics/coupling.py ../v1/app/helpdesk --name chk --out-dir /tmp/chk --no-plot \
  && diff /tmp/chk/chk.csv metrics/results/v1-coupled.csv; git worktree remove ../v1
```

Medição da `main` e conferência da zona de dor ([saída](../evidence/f08/pain-zone-check.txt)):

```bash
python metrics/coupling.py app/helpdesk --name main
python - <<'EOF'
import csv
for r in csv.DictReader(open("metrics/results/main.csv")):
    a, i, d = float(r["a"]), float(r["i"]), float(r["d"])
    if a < 0.5 and i < 0.5 and d >= 0.5: print("ZONA DE DOR:", r["component"])
EOF
# → ZONA DE DOR: schemas
```
