"""Valida o catálogo de KPIs e imprime um resumo por área.

Uso: python catalogo/validar_catalogo.py
"""

import csv
import sys
from collections import Counter
from pathlib import Path

CAMINHO = Path(__file__).with_name("kpis.csv")
COLUNAS = ["id", "area", "kpi", "formula", "unidade", "polaridade", "tipo", "frequencia", "fonte_tipica", "contrapeso"]
POLARIDADES = {"maior", "menor", "faixa"}
TIPOS = {"leading", "lagging"}


def validar(linhas):
    erros = []
    ids = [l["id"] for l in linhas]
    for dup, n in Counter(ids).items():
        if n > 1:
            erros.append(f"ID duplicado: {dup}")
    for l in linhas:
        if l["polaridade"] not in POLARIDADES:
            erros.append(f"{l['id']}: polaridade inválida '{l['polaridade']}'")
        if l["tipo"] not in TIPOS:
            erros.append(f"{l['id']}: tipo inválido '{l['tipo']}'")
        if l["contrapeso"] and l["contrapeso"] not in ids:
            erros.append(f"{l['id']}: contrapeso inexistente '{l['contrapeso']}'")
        for campo in ("kpi", "formula", "unidade"):
            if not l[campo].strip():
                erros.append(f"{l['id']}: campo '{campo}' vazio")
    return erros


def main():
    with CAMINHO.open(encoding="utf-8") as f:
        leitor = csv.DictReader(f, delimiter=";")
        if leitor.fieldnames != COLUNAS:
            print(f"Cabeçalho inesperado: {leitor.fieldnames}")
            return 1
        linhas = list(leitor)

    erros = validar(linhas)
    por_area = Counter(l["area"] for l in linhas)
    leading = Counter(l["area"] for l in linhas if l["tipo"] == "leading")

    print(f"{len(linhas)} KPIs no catálogo\n")
    print(f"{'área':<16}{'total':>6}{'leading':>9}")
    for area, total in por_area.items():
        print(f"{area:<16}{total:>6}{leading[area]:>9}")

    if erros:
        print("\nErros:")
        for e in erros:
            print(f"  - {e}")
        return 1
    print("\nCatálogo válido.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
