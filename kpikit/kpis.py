"""Cálculo dos KPIs do catálogo a partir das tabelas fato.

Regra de agregação (erro clássico de painel): razões são sempre agregadas
como Σnumerador / Σdenominador — nunca como média das razões diárias, que
dá o mesmo peso a um domingo de 5 mil pedidos e a uma Black Friday de 400 mil.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

from kpikit import config as cfg

Coluna = str | Callable[[pd.DataFrame], pd.Series]


@dataclass(frozen=True)
class DefKPI:
    nome: str
    tabela: str
    num: Coluna
    den: Coluna | None = None
    escala: float = 1.0
    modo: str = "razao"  # razao | ponderada | soma
    formato: str = "{:.2%}"


def _col(df: pd.DataFrame, c: Coluna) -> pd.Series:
    return c(df) if callable(c) else df[c]


def _e_3pl(df: pd.DataFrame) -> pd.Series:
    return df["pedidos"].where(df["modelo"] == "3PL", 0)


def _capacidade_veiculo(df: pd.DataFrame) -> pd.Series:
    return df["viagens"] * 1_800


REGISTRO: dict[str, DefKPI] = {
    "SC-006": DefKPI(
        "Dock-to-stock P90 (h)", "fato_cd", "dock_to_stock_p90_h", "pedidos", modo="ponderada", formato="{:.1f} h"
    ),
    "SC-007": DefKPI(
        "Acurácia de picking",
        "fato_cd",
        lambda d: d.linhas_separadas - d.linhas_com_erro,
        "linhas_separadas",
        formato="{:.3%}",
    ),
    "SC-008": DefKPI("Produtividade (linhas/HH)", "fato_cd", "linhas_separadas", "horas_homem", formato="{:.1f}"),
    "SC-009": DefKPI("Expedição no cut-off", "fato_cd", "pedidos_expedidos_cutoff", "pedidos"),
    "SC-012": DefKPI(
        "Utilização de capacidade do CD", "fato_cd", "utilizacao", "pedidos", modo="ponderada", formato="{:.1%}"
    ),
    "MM-001": DefKPI("On-time departure", "fato_linehaul", "partidas_no_horario", "viagens"),
    "MM-002": DefKPI("On-time arrival", "fato_linehaul", "chegadas_na_janela", "viagens"),
    "MM-003": DefKPI("Ocupação de veículo", "fato_linehaul", "volumes", _capacidade_veiculo, formato="{:.1%}"),
    "MM-004": DefKPI("Custo por kg transferido", "fato_linehaul", "custo_frete", "kg", formato="R$ {:.3f}"),
    "MM-005": DefKPI(
        "Dwell time P90 (h)", "fato_hub", "dwell_time_p90_h", "volumes_triados", modo="ponderada", formato="{:.1f} h"
    ),
    "MM-006": DefKPI(
        "Missort (PPM)", "fato_hub", "volumes_missort", "volumes_triados", escala=1e6, formato="{:.0f} PPM"
    ),
    "MM-007": DefKPI("Backlog na onda", "fato_hub", "backlog_fechamento_onda", modo="soma", formato="{:,.0f}"),
    "MM-009": DefKPI("Km vazio", "fato_linehaul", "km_vazio", "km_total", formato="{:.1%}"),
    "MM-010": DefKPI("Dependência de 3PL (% pedidos)", "fato_cd", _e_3pl, "pedidos", formato="{:.1%}"),
    "LM-001": DefKPI("OTD vs. promessa", "fato_last_mile", "entregues_no_prazo", "pedidos_promessa_vencida"),
    "LM-002": DefKPI("FADR", "fato_last_mile", "entregues_primeira_tentativa", "pacotes_em_rota"),
    "LM-003": DefKPI("Custo por entrega", "fato_last_mile", "custo_operacao", "entregues_total", formato="R$ {:.2f}"),
    "LM-004": DefKPI("Paradas por hora", "fato_last_mile", "paradas", "horas_em_rota", formato="{:.1f}"),
    "LM-006": DefKPI(
        "Ocorrências por 10k", "fato_last_mile", "ocorrencias", "pacotes_em_rota", escala=1e4, formato="{:.1f}"
    ),
    "LM-007": DefKPI(
        "Contatos SAC por 100 pedidos",
        "fato_last_mile",
        "contatos_sac",
        "pacotes_em_rota",
        escala=100,
        formato="{:.2f}",
    ),
    "LM-008": DefKPI("Tentativa falsa", "fato_last_mile", "tentativas_falsas", "tentativas_malsucedidas"),
    "LM-011": DefKPI("Entregues em até 48h", "fato_last_mile", "entregues_ate_48h", "pacotes_em_rota"),
    "MK-001": DefKPI("ROAS (plataforma)", "fato_midia", "receita_atribuida", "investimento", formato="{:.2f}x"),
    "MK-002": DefKPI("POAS", "fato_midia", "lucro_bruto_atribuido", "investimento", formato="{:.2f}x"),
    "MK-004": DefKPI("CAC", "fato_midia", "investimento", "novos_clientes", formato="R$ {:.2f}"),
    "MK-007": DefKPI("CTR", "fato_midia", "cliques", "impressoes"),
    "PE-002": DefKPI("Turnover mensal", "fato_pessoas", "desligamentos", "headcount"),
    # Só coortes maduras: quem entrou há menos de 90 dias ainda pode sair (censura à direita).
    "PE-003": DefKPI(
        "Turnover precoce (<90d)",
        "fato_pessoas",
        lambda d: d.desligamentos_menos_90d.where(d.coorte_madura, 0),
        lambda d: d.admissoes.where(d.coorte_madura, 0),
    ),
    "PE-008": DefKPI(
        "Taxa de frequência de acidentes",
        "fato_pessoas",
        "acidentes",
        "horas_trabalhadas",
        escala=1e6,
        formato="{:.2f}",
    ),
    "PE-009": DefKPI(
        "Taxa de gravidade", "fato_pessoas", "dias_perdidos", "horas_trabalhadas", escala=1e6, formato="{:.1f}"
    ),
}


def _preparar(dados: dict[str, pd.DataFrame], tabela: str) -> pd.DataFrame:
    df = dados[tabela].copy()
    if "unidade_id" in df and "regiao_id" not in df:
        df = df.merge(
            dados["dim_unidade"][["unidade_id", "regiao_id", "modelo", "tipo"]].drop(
                columns=[c for c in ("modelo",) if c in df]
            ),
            on="unidade_id",
            how="left",
        )
    if "data" not in df and "mes" in df:
        df["data"] = df["mes"]
    return df


def calcular(
    dados: dict[str, pd.DataFrame], kpi_id: str, freq: str | None = None, por: str | None = None, inicio=None, fim=None
) -> pd.Series:
    """Calcula um KPI.

    freq: None (total do período), 'D', 'W', 'MS' ou 'QS'.
    por:  dimensão de corte (ex.: 'unidade_id', 'regiao_id', 'modelo', 'canal').
    """
    d = REGISTRO[kpi_id]
    df = _preparar(dados, d.tabela)
    if inicio is not None:
        df = df[df.data >= pd.Timestamp(inicio)]
    if fim is not None:
        df = df[df.data <= pd.Timestamp(fim)]

    if d.modo == "ponderada":
        peso = _col(df, d.den)
        df = df.assign(_n=_col(df, d.num).fillna(0) * peso, _d=peso.where(_col(df, d.num).notna(), 0))
    else:
        df = df.assign(_n=_col(df, d.num), _d=_col(df, d.den) if d.den is not None else 1)

    chaves = []
    if freq:
        chaves.append(pd.Grouper(key="data", freq=freq))
    if por:
        chaves.append(por)
    agg = df.groupby(chaves)[["_n", "_d"]].sum() if chaves else df[["_n", "_d"]].sum().to_frame().T

    if d.modo == "soma":
        res = agg["_n"]
    else:
        res = agg["_n"] / agg["_d"].where(agg["_d"] != 0)
    res = res * d.escala
    res.name = kpi_id
    return res.iloc[0] if not chaves else res


def mer(dados: dict[str, pd.DataFrame], freq: str | None = None) -> pd.Series | float:
    """MK-003 — Marketing Efficiency Ratio: receita total / investimento total (imune à atribuição)."""
    rec = dados["fato_demanda"].groupby(pd.Grouper(key="data", freq=freq or "YS")).receita.sum()
    inv = dados["fato_midia"].groupby(pd.Grouper(key="data", freq=freq or "YS")).investimento.sum()
    serie = rec / inv
    return serie if freq else float(serie.iloc[0])


def formatar(kpi_id: str, valor: float) -> str:
    return REGISTRO[kpi_id].formato.format(valor)


def linha_base(dados: dict[str, pd.DataFrame], inicio="2025-07-01", fim="2025-12-31") -> dict[str, float]:
    """Linha de base do caso: 2º semestre de 2025 (inclui o pico de fim de ano)."""
    return {m.kpi_id: float(calcular(dados, m.kpi_id, inicio=inicio, fim=fim)) for m in cfg.METAS_2026}


def painel_metas(dados: dict[str, pd.DataFrame]) -> pd.DataFrame:
    base = linha_base(dados)
    linhas = []
    for m in cfg.METAS_2026:
        b = base[m.kpi_id]
        sinal = 1 if m.polaridade == "maior" else -1
        linhas.append(
            {
                "kpi_id": m.kpi_id,
                "kpi": m.nome,
                "linha_base": b,
                "meta_2026": m.meta,
                "benchmark": m.benchmark,
                "fonte_benchmark": m.fonte_benchmark,
                "confianca": m.nivel_confianca,
                "gap_para_meta": sinal * (m.meta - b),
                "vs_benchmark": None if m.benchmark is None else sinal * (b - m.benchmark),
                "polaridade": m.polaridade,
            }
        )
    return pd.DataFrame(linhas)
