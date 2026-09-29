"""Verifica a documentação: links relativos quebrados e IDs de KPI citados fora do catálogo.

Uso: python catalogo/verificar_docs.py
"""

import csv
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
KPI = re.compile(r"\b(?:SC|MM|LM|PE|MK|PJ|AG|LS)-\d{3}\b")
IGNORAR = {".venv", ".git", "node_modules"}


def arquivos_md():
    return [p for p in RAIZ.rglob("*.md") if not IGNORAR.intersection(p.relative_to(RAIZ).parts)]


def main() -> int:
    with (RAIZ / "catalogo" / "kpis.csv").open(encoding="utf-8") as f:
        ids = {linha["id"] for linha in csv.DictReader(f, delimiter=";")}
    erros = []
    for md in arquivos_md():
        texto = md.read_text(encoding="utf-8")
        rel = md.relative_to(RAIZ)
        for alvo in LINK.findall(texto):
            if alvo.startswith(("http://", "https://", "mailto:", "#")):
                continue
            caminho = (md.parent / alvo.split("#")[0]).resolve()
            if not caminho.exists():
                erros.append(f"{rel}: link quebrado → {alvo}")
        for kpi in sorted(set(KPI.findall(texto)) - ids):
            erros.append(f"{rel}: {kpi} citado mas ausente do catálogo")
    codigo = [*RAIZ.glob("notebooks/nb_*.py"), *RAIZ.glob("app/*.py"), *RAIZ.glob("kpikit/*.py")]
    for py in codigo:
        for kpi in sorted(set(KPI.findall(py.read_text(encoding="utf-8"))) - ids):
            erros.append(f"{py.relative_to(RAIZ)}: {kpi} citado mas ausente do catálogo")
    print(f"{len(arquivos_md())} arquivos Markdown e {len(codigo)} arquivos de código verificados")
    for e in erros:
        print(f"  - {e}")
    return 1 if erros else 0


if __name__ == "__main__":
    sys.exit(main())
