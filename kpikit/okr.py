"""Pontuação de OKRs a partir dos dados (sem planilha).

Nota de KR (padrão Google/Doerr, escala 0–1):
    nota = (atual − linha de base) / (meta − linha de base), limitada a [0, 1]
A mesma fórmula serve para KRs "menor é melhor", porque numerador e denominador trocam de sinal juntos.
Leitura: committed espera 1,0; aspirational com 0,6–0,7 já é sucesso.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from kpikit import kpis

ARQUIVO_PADRAO = Path(__file__).resolve().parent.parent / "caso-integrado" / "okrs_2026.json"


def nota_kr(base: float, meta: float, atual: float) -> float:
    if meta == base:
        return 1.0 if atual == meta else 0.0
    return float(min(max((atual - base) / (meta - base), 0.0), 1.0))


def status(nota: float, tipo: str) -> str:
    alvo = 1.0 if tipo == "committed" else 0.7
    if nota >= alvo:
        return "atingido"
    if nota >= alvo * 0.6:
        return "em risco"
    return "fora da rota"


def _valor(dados, kpi_id: str, periodo, filtro: dict | None) -> float:
    if not filtro:
        return float(kpis.calcular(dados, kpi_id, inicio=periodo[0], fim=periodo[1]))
    ((dim, valor),) = filtro.items()
    serie = kpis.calcular(dados, kpi_id, por=dim, inicio=periodo[0], fim=periodo[1])
    return float(serie.loc[valor])


def carregar_okrs(arquivo: Path = ARQUIVO_PADRAO) -> dict:
    return json.loads(Path(arquivo).read_text(encoding="utf-8"))


def pontuar(dados: dict[str, pd.DataFrame], okrs: dict | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Retorna (tabela de KRs, tabela de objetivos com nota média e checagem de contrapeso)."""
    okrs = okrs or carregar_okrs()
    pb, pa = okrs["periodo_linha_base"], okrs["periodo_atual"]
    krs, objs = [], []
    for o in okrs["objetivos"]:
        notas = []
        for kr in o["krs"]:
            base = _valor(dados, kr["kpi_id"], pb, kr.get("filtro"))
            # Um KR pode ter período próprio (ex.: coorte que já completou 90 dias).
            atual = _valor(dados, kr["kpi_id"], kr.get("periodo_atual", pa), kr.get("filtro"))
            n = nota_kr(base, kr["meta"], atual)
            notas.append(n)
            krs.append(
                {
                    "objetivo": o["id"],
                    "kr": kr["id"],
                    "descricao": kr["descricao"],
                    "kpi_id": kr["kpi_id"],
                    "tipo": kr["tipo"],
                    "linha_base": base,
                    "meta": kr["meta"],
                    "atual": atual,
                    "nota": n,
                    "status": status(n, kr["tipo"]),
                }
            )
        cp = o.get("contrapeso")
        cp_ok = None
        if cp:
            v = _valor(dados, cp["kpi_id"], pa, None)
            cp_ok = v <= cp["limite"] if cp["polaridade"] == "menor" else v >= cp["limite"]
        objs.append(
            {
                "objetivo": o["id"],
                "pilar": o["pilar"],
                "descricao": o["objetivo"],
                "dono": o["dono"],
                "nota_media": sum(notas) / len(notas),
                "contrapeso": cp["descricao"] if cp else "",
                "contrapeso_ok": cp_ok,
            }
        )
    return pd.DataFrame(krs), pd.DataFrame(objs)
