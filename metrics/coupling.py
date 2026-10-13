"""Mede o acoplamento de um pacote Python pela régua fixa do requisito 3 do desafio.

    python metrics/coupling.py <caminho/para/app/helpdesk> --name <rotulo> [--out-dir metrics/results]

Grava <out-dir>/<rotulo>.csv (cabeçalho exato `component,ca,ce,i,a,d`) e <out-dir>/<rotulo>.png
(gráfico A × I com a Main Sequence). Para medir uma tag, rode este script sobre um checkout dela:

    git worktree add ../v1 v1-coupled
    python metrics/coupling.py ../v1/app/helpdesk --name v1-coupled
    git worktree remove ../v1

Régua (requisito 3, sem adaptações):
- Componente: cada módulo .py do pacote, incluindo subpastas, identificado pelo caminho com pontos a
  partir da raiz medida (ex.: `adapters.gateway`), exceto os `__init__.py`.
- Dependência: um import, relativo ou absoluto, que resolve para outro componente
  (ex.: `from ..ports import Gateway` ou `from helpdesk import config`). Bibliotecas externas e da
  biblioteca padrão não contam.
- Ca: quantos componentes importam este. Ce: quantos componentes este importa.
- I = Ce / (Ce + Ca), ou 0 quando os dois são zero.
- A = classes abstratas (que herdam de `typing.Protocol` ou `abc.ABC`) / total de classes do módulo,
  ou 0 quando o módulo não tem classes.
- D = |A + I - 1|. Valores arredondados para 2 casas.

Interpretações onde a régua não é explícita (registradas no ADR da métrica):
- O nome do pacote raiz é o nome da pasta medida (`helpdesk`); `import helpdesk.x` e
  `from helpdesk import x` resolvem para o componente `x`.
- `from <pacote> import nome` depende de `<pacote>.nome` quando ele é um componente; senão, de
  `<pacote>` quando ele é um componente. Imports para pacotes (`__init__`) não contam.
- Todo import do módulo conta, inclusive dentro de funções e de `if TYPE_CHECKING:`; cada componente
  importado conta uma vez (conjunto); autoimport não conta.
- Classes: todo `class` do módulo, inclusive aninhadas. Abstrata é a que tem, entre as bases diretas,
  `Protocol`/`ABC` (nome simples, `typing.`/`typing_extensions.`/`abc.`, ou `Protocol[T]`).
- Arredondamento "meio para cima" (ROUND_HALF_UP) sobre o valor exato; D é calculado com A e I
  exatos e só então arredondado. O CSV escreve i, a e d sempre com 2 casas.
"""

import argparse
import ast
import csv
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction
from pathlib import Path

ABSTRACT_BASES = {"Protocol", "ABC"}
ABSTRACT_MODULES = {"typing", "typing_extensions", "abc"}
HEADER = ["component", "ca", "ce", "i", "a", "d"]


@dataclass(frozen=True)
class Metrics:
    component: str
    ca: int
    ce: int
    i: Fraction
    a: Fraction
    d: Fraction

    def row(self) -> list[str]:
        return [self.component, str(self.ca), str(self.ce), fmt(self.i), fmt(self.a), fmt(self.d)]


def fmt(value: Fraction) -> str:
    exact = Decimal(value.numerator) / Decimal(value.denominator)
    return str(exact.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def discover(root: Path) -> dict[str, Path]:
    """Componente (caminho com pontos relativo à raiz) → arquivo."""
    components = {}
    for path in sorted(root.rglob("*.py")):
        if path.name == "__init__.py":
            continue
        relative = path.relative_to(root).with_suffix("")
        components[".".join(relative.parts)] = path
    return components


def is_abstract(base: ast.expr) -> bool:
    if isinstance(base, ast.Subscript):  # Protocol[T]
        base = base.value
    if isinstance(base, ast.Name):
        return base.id in ABSTRACT_BASES
    if isinstance(base, ast.Attribute) and isinstance(base.value, ast.Name):
        return base.attr in ABSTRACT_BASES and base.value.id in ABSTRACT_MODULES
    return False


def resolve_imports(tree: ast.AST, component: str, root_name: str, components: set[str]) -> set[str]:
    # Nome do módulo relativo à raiz, como lista; o pacote que o contém é tudo menos o último item.
    package = component.split(".")[:-1]
    found: set[str] = set()

    def strip_root(dotted: str) -> str | None:
        if dotted == root_name:
            return ""
        if dotted.startswith(root_name + "."):
            return dotted[len(root_name) + 1:]
        return None

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                target = strip_root(alias.name)
                if target in components:
                    found.add(target)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                if node.level - 1 > len(package):
                    continue  # sobe acima da raiz medida
                base_parts = package[:len(package) - (node.level - 1)]
                if node.module:
                    base_parts = base_parts + node.module.split(".")
                base = ".".join(base_parts)
            else:
                base = strip_root(node.module or "")
                if base is None:
                    continue  # biblioteca externa ou padrão
            for alias in node.names:
                candidate = f"{base}.{alias.name}" if base else alias.name
                if candidate in components:
                    found.add(candidate)
                elif base in components:
                    found.add(base)
    found.discard(component)
    return found


def measure(root: Path) -> list[Metrics]:
    root = root.resolve()
    files = discover(root)
    names = set(files)
    efferent: dict[str, set[str]] = {}
    classes: dict[str, tuple[int, int]] = {}
    for component, path in files.items():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        efferent[component] = resolve_imports(tree, component, root.name, names)
        defs = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        abstract = sum(1 for node in defs if any(is_abstract(base) for base in node.bases))
        classes[component] = (abstract, len(defs))

    result = []
    for component in sorted(files):
        ce = len(efferent[component])
        ca = sum(1 for other, deps in efferent.items() if component in deps)
        i = Fraction(ce, ce + ca) if ce + ca else Fraction(0)
        abstract, total = classes[component]
        a = Fraction(abstract, total) if total else Fraction(0)
        d = abs(a + i - 1)
        result.append(Metrics(component, ca, ce, i, a, d))
    return result


def write_csv(metrics: list[Metrics], path: Path) -> None:
    with open(path, "w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(HEADER)
        writer.writerows(m.row() for m in metrics)


def plot(metrics: list[Metrics], path: Path, title: str) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.fill([0, 0.5, 0], [0, 0, 0.5], color="#d9534f", alpha=0.15, label="zona de dor (A<0,5, I<0,5, D≥0,5)")
    ax.fill([1, 0.5, 1], [1, 1, 0.5], color="#f0ad4e", alpha=0.15, label="zona de inutilidade")
    ax.plot([0, 1], [1, 0], color="#337ab7", linewidth=1.5, label="Main Sequence (A + I = 1)")

    groups: dict[tuple[float, float], list[str]] = {}
    for m in metrics:
        groups.setdefault((float(fmt(m.i)), float(fmt(m.a))), []).append(m.component)
    previous: tuple[float, float] | None = None
    below = False
    for (i, a), names in sorted(groups.items(), key=lambda item: (item[0][1], item[0][0])):
        ax.scatter(i, a, s=60, color="#222222", zorder=3)
        # Pontos vizinhos na mesma altura alternam o rótulo entre acima e abaixo para não sobrepor.
        near = previous is not None and abs(previous[1] - a) < 0.08 and abs(previous[0] - i) < 0.2
        below = (not below) if near else False
        label = "\n".join(sorted(names))
        offset = (6, -10 - 10 * len(names)) if below else (6, 6)
        ax.annotate(label, (i, a), textcoords="offset points", xytext=offset, fontsize=8)
        previous = (i, a)

    ax.set_xlim(-0.05, 1.1)
    ax.set_ylim(-0.05, 1.1)
    ax.set_xlabel("I (instabilidade) = Ce / (Ce + Ca)")
    ax.set_ylabel("A (abstração) = classes abstratas / classes")
    ax.set_title(f"Acoplamento: {title}")
    ax.grid(True, linestyle=":", linewidth=0.5)
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", type=Path, help="pasta do pacote a medir (ex.: app/helpdesk)")
    parser.add_argument("--name", required=True, help="rótulo da medição (nome dos arquivos de saída)")
    parser.add_argument("--out-dir", type=Path, default=Path(__file__).parent / "results")
    parser.add_argument("--no-plot", action="store_true", help="grava só o CSV")
    args = parser.parse_args()

    if not args.path.is_dir():
        parser.error(f"{args.path} não é uma pasta")
    metrics = measure(args.path)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(metrics, args.out_dir / f"{args.name}.csv")
    if not args.no_plot:
        plot(metrics, args.out_dir / f"{args.name}.png", args.name)
    print(",".join(HEADER))
    for m in metrics:
        print(",".join(m.row()))


if __name__ == "__main__":
    main()
