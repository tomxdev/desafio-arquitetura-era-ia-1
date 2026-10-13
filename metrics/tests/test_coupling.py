"""Testes do script de métrica: casos de borda da régua e o oráculo da v1-coupled."""

import csv
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "metrics"))

from coupling import fmt, measure  # noqa: E402

V1_FIXTURE = Path(__file__).parent / "fixtures" / "v1" / "helpdesk"

# Calculado à mão pela régua do requisito 3 (docs/implementation-master-plan.md, tabela 1.1).
V1_ORACLE = [
    ["component", "ca", "ce", "i", "a", "d"],
    ["classification", "1", "3", "0.75", "0.00", "0.25"],
    ["config", "6", "0", "0.00", "0.00", "1.00"],
    ["extraction", "1", "3", "0.75", "0.00", "0.25"],
    ["llm", "4", "1", "0.20", "0.00", "0.80"],
    ["main", "0", "5", "1.00", "0.00", "0.00"],
    ["report", "1", "4", "0.80", "0.00", "0.20"],
    ["schemas", "5", "0", "0.00", "0.00", "1.00"],
    ["suggestion", "1", "3", "0.75", "0.00", "0.25"],
    ["tickets", "1", "1", "0.50", "0.00", "0.50"],
]


def make_package(tmp_path: Path, files: dict[str, str], name: str = "helpdesk") -> Path:
    root = tmp_path / name
    for relative, source in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
    return root


def by_name(metrics):
    return {m.component: m for m in metrics}


def test_v1_oracle_via_cli(tmp_path):
    subprocess.run([sys.executable, str(ROOT / "metrics" / "coupling.py"), str(V1_FIXTURE),
                    "--name", "v1", "--out-dir", str(tmp_path), "--no-plot"],
                   check=True, capture_output=True)
    with open(tmp_path / "v1.csv", encoding="utf-8", newline="") as file:
        assert list(csv.reader(file)) == V1_ORACLE


def test_csv_header_and_png(tmp_path):
    subprocess.run([sys.executable, str(ROOT / "metrics" / "coupling.py"), str(V1_FIXTURE),
                    "--name", "v1", "--out-dir", str(tmp_path)], check=True, capture_output=True)
    assert (tmp_path / "v1.csv").read_text(encoding="utf-8").splitlines()[0] == "component,ca,ce,i,a,d"
    assert (tmp_path / "v1.png").read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_versioned_v1_csv_matches_oracle():
    with open(ROOT / "metrics" / "results" / "v1-coupled.csv", encoding="utf-8", newline="") as file:
        assert list(csv.reader(file)) == V1_ORACLE


def test_relative_absolute_and_subpackages(tmp_path):
    root = make_package(tmp_path, {
        "__init__.py": "",
        "ports.py": "from typing import Protocol\nclass Gateway(Protocol):\n    def complete(self) -> str: ...\n",
        "adapters/__init__.py": "",
        "adapters/gateway.py": "import json\nimport httpx\nfrom ..ports import Gateway\n",
        "features/__init__.py": "",
        "features/classify.py": "from helpdesk import ports\nfrom helpdesk.ports import Gateway\n",
        "main.py": "from .adapters import gateway\nimport helpdesk.features.classify\nfrom . import ports\n",
    })
    m = by_name(measure(root))
    assert set(m) == {"ports", "adapters.gateway", "features.classify", "main"}  # sem __init__
    assert (m["adapters.gateway"].ce, m["adapters.gateway"].ca) == (1, 1)  # stdlib/terceiros não contam
    assert (m["features.classify"].ce, m["features.classify"].ca) == (1, 1)  # mesmo alvo conta uma vez
    assert (m["main"].ce, m["main"].ca) == (3, 0)
    assert (m["ports"].ce, m["ports"].ca) == (0, 3)
    assert m["ports"].a == 1 and m["ports"].d == 0


def test_abstract_classes(tmp_path):
    root = make_package(tmp_path, {
        "kinds.py": (
            "import abc\nimport typing\nfrom abc import ABC, ABCMeta\nfrom typing import Generic, Protocol, TypeVar\n"
            "T = TypeVar('T')\n"
            "class P1(Protocol): ...\n"
            "class P2(typing.Protocol): ...\n"
            "class P3(Protocol[T]): ...\n"
            "class A1(ABC): ...\n"
            "class A2(abc.ABC): ...\n"
            "class Meta(metaclass=ABCMeta): ...\n"   # não herda de ABC: concreta pela régua
            "class Child(P1): ...\n"                 # herança indireta: concreta pela régua
            "class Plain:\n    class Nested: ...\n"  # aninhada conta como classe
        ),
        "empty.py": "VALUE = 1\n",
    })
    m = by_name(measure(root))
    assert m["kinds"].a == Fraction(5, 9)
    assert m["empty"].a == 0  # sem classes


def test_isolated_component_and_imports_inside_functions(tmp_path):
    root = make_package(tmp_path, {
        "alone.py": "import os\n",
        "lazy.py": "def f():\n    from . import alone\n    return alone\n",
        "self_ref.py": "from . import self_ref\n",
    })
    m = by_name(measure(root))
    assert (m["alone"].ca, m["alone"].ce) == (1, 0)
    assert m["lazy"].ce == 1
    assert (m["self_ref"].ce, m["self_ref"].ca, m["self_ref"].i) == (0, 0, 0)  # autoimport não conta; I=0
    assert m["self_ref"].d == 1


def test_relative_import_above_root_is_ignored(tmp_path):
    root = make_package(tmp_path, {"mod.py": "from ... import something\n"})
    assert by_name(measure(root))["mod"].ce == 0


@pytest.mark.parametrize("value, text", [
    (Fraction(1, 8), "0.13"),   # meio para cima (round() do Python daria 0.12)
    (Fraction(2, 3), "0.67"),
    (Fraction(1, 3), "0.33"),
    (Fraction(1), "1.00"),
    (Fraction(0), "0.00"),
])
def test_rounding(value, text):
    assert fmt(value) == text
