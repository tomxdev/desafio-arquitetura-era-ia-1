# 0008. Medir o acoplamento pela régua fixa e declarar as exceções estáveis por natureza

- Status: proposta (rascunho da F03; exceções e leitura final na F08)
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
- Componentes concretos que quase nunca mudam caem na zona de dor pela fórmula. Candidato a exceção "estável por natureza": `schemas` (tipos de valor do contrato HTTP, fixados pela suíte de caracterização). **Não** podem ser exceção: o componente que chama o gateway e os componentes das features. A lista final é decidida na F08, com a medição da `main`.
- A métrica aponta onde olhar; não justifica sozinha uma mudança de estrutura (nenhum import "para sair da zona").

## Evidência

```bash
python -m pytest metrics/tests -q
git worktree add ../v1 v1-coupled && python metrics/coupling.py ../v1/app/helpdesk --name chk --out-dir /tmp/chk --no-plot \
  && diff /tmp/chk/chk.csv metrics/results/v1-coupled.csv; git worktree remove ../v1
```
