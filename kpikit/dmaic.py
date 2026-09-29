"""Projeto DMAIC: dock-to-stock do CD-AM1 (Manaus).

Dados de estudo, no nível de cada recebimento (nota fiscal/carga), coletados em três janelas:
    medir     2026-02-02 → 2026-03-29   linha de base
    piloto    2026-06-01 → 2026-07-26   após as melhorias
    controle  2026-07-27 → 2026-09-27   sustentação

Os fatores de causa são premissas do caso (camada D). O objetivo é demonstrar o método:
Pareto → testes de hipótese → modelo → piloto → capability não normal → controle por fases.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

JANELAS = {
    "medir": ("2026-02-02", "2026-03-29"),
    "piloto": ("2026-06-01", "2026-07-26"),
    "controle": ("2026-07-27", "2026-09-27"),
}
LSE_HORAS = 12.0  # SLA de dock-to-stock contratado com o comercial
ETAPAS = ["espera_doca_h", "descarga_h", "conferencia_h", "tratativa_divergencia_h", "armazenagem_h"]
FORNECEDORES = [f"F{i:02d}" for i in range(1, 13)]
PESO_FORNECEDOR = np.array([22, 16, 13, 10, 8, 7, 6, 5, 4, 4, 3, 2], dtype=float)
FORNECEDORES_CRITICOS = {"F03", "F07"}  # alta divergência e carga batida


def gerar_recebimentos(semente: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(semente)
    linhas = []
    for fase, (ini, fim) in JANELAS.items():
        depois = fase != "medir"
        for dia in pd.date_range(ini, fim, freq="D"):
            if dia.dayofweek == 6:  # sem recebimento aos domingos
                continue
            n = rng.poisson(26 if dia.dayofweek < 5 else 12)
            forn = rng.choice(FORNECEDORES, n, p=PESO_FORNECEDOR / PESO_FORNECEDOR.sum())
            critico = np.isin(forn, list(FORNECEDORES_CRITICOS))
            # Melhoria 4: desenvolvimento de fornecedor (paletização padrão para F03 e F07).
            p_batida = np.where(critico, 0.35 if depois else 0.70, 0.25)
            tipo = np.where(rng.random(n) < p_batida, "batida", np.where(rng.random(n) < 0.7, "paletizada", "mista"))
            # Melhoria 1: agendamento obrigatório por janela (portal do fornecedor).
            agendado = rng.random(n) < (0.92 if depois else 0.40)
            # Melhoria 2: ASN/XML antecipado + conferência cega por scanner.
            asn = rng.random(n) < (0.85 if depois else 0.30)
            hora = np.clip(rng.normal(13, 3.2, n), 6, 23.5)
            turno = np.where(hora < 14, "manha", np.where(hora < 22, "tarde", "noite"))
            skus = rng.integers(3, 60, n)
            volumes = np.round(skus * rng.uniform(4, 18, n)).astype(int)

            fila = np.where(agendado, rng.gamma(2, 0.25, n), rng.gamma(2, 1.4, n)) + 0.8 * (
                ~agendado & (turno == "tarde")
            )
            descarga = {"paletizada": 0.4, "mista": 0.9, "batida": 1.8}
            descarga = np.array([descarga[t] for t in tipo]) * rng.lognormal(0, 0.25, n) + volumes / 2000
            conferencia = (0.5 + 0.02 * skus) * np.where(asn, 0.5, 1.0) * rng.lognormal(0, 0.2, n)
            p_div = np.where(critico, 0.40, 0.14) * np.where(asn, 0.45, 1.0)
            divergencia = rng.random(n) < p_div
            # Melhoria 3: recebe o conforme e segrega só o divergente (não trava a NF inteira).
            media_tratativa = 0.8 if depois else 4.2
            tratativa = np.where(divergencia, rng.gamma(1.6, media_tratativa / 1.6, n), 0.0)
            armazenagem = rng.gamma(4, 0.2, n) + 0.6 * (turno == "noite")
            linhas.append(
                pd.DataFrame(
                    {
                        "chegada": dia + pd.to_timedelta(hora, unit="h"),
                        "fase": fase,
                        "fornecedor": forn,
                        "fornecedor_critico": critico,
                        "tipo_carga": tipo,
                        "agendado": agendado,
                        "asn_antecipado": asn,
                        "turno_chegada": turno,
                        "skus": skus,
                        "volumes": volumes,
                        "divergencia": divergencia,
                        "espera_doca_h": fila,
                        "descarga_h": descarga,
                        "conferencia_h": conferencia,
                        "tratativa_divergencia_h": tratativa,
                        "armazenagem_h": armazenagem,
                    }
                )
            )
    df = pd.concat(linhas, ignore_index=True)
    df[ETAPAS] = df[ETAPAS].round(2)
    df["dock_to_stock_h"] = df[ETAPAS].sum(axis=1).round(2)
    df.insert(0, "recebimento_id", [f"R{i:05d}" for i in range(1, len(df) + 1)])
    return df


# ---------------------------------------------------------------- Medir / Analisar
def pareto(df: pd.DataFrame, valores: list[str] = ETAPAS, so_cauda: bool = False) -> pd.DataFrame:
    """Pareto das horas por etapa. so_cauda=True olha só os recebimentos acima do SLA:
    a média e a cauda costumam ter causas diferentes, e o SLA é violado pela cauda."""
    if so_cauda:
        df = df[df.dock_to_stock_h > LSE_HORAS]
    total = df[valores].sum().sort_values(ascending=False)
    return pd.DataFrame(
        {"horas": total.round(0), "pct": total / total.sum(), "pct_acumulado": (total / total.sum()).cumsum()}
    )


def comparar_grupos(df: pd.DataFrame, fator: str, y: str = "dock_to_stock_h") -> dict:
    """Dois grupos: Welch t e Mann-Whitney (dados assimétricos). 3+: ANOVA e Kruskal-Wallis."""
    grupos = {k: g[y].to_numpy() for k, g in df.groupby(fator)}
    resumo = df.groupby(fator)[y].agg(n="size", media="mean", mediana="median", p90=lambda s: s.quantile(0.9)).round(2)
    if len(grupos) == 2:
        a, b = grupos.values()
        return {
            "resumo": resumo,
            "welch_t_p": float(stats.ttest_ind(a, b, equal_var=False).pvalue),
            "mann_whitney_p": float(stats.mannwhitneyu(a, b).pvalue),
        }
    return {
        "resumo": resumo,
        "anova_p": float(stats.f_oneway(*grupos.values()).pvalue),
        "kruskal_p": float(stats.kruskal(*grupos.values()).pvalue),
    }


def qui_quadrado(df: pd.DataFrame, linha: str, coluna: str = "divergencia") -> dict:
    tabela = pd.crosstab(df[linha], df[coluna])
    qui2, p, gl, _ = stats.chi2_contingency(tabela)
    taxa = pd.crosstab(df[linha], df[coluna], normalize="index")
    return {
        "tabela": tabela,
        "taxa": taxa.get(True, taxa.iloc[:, -1]).round(3),
        "qui2": float(qui2),
        "gl": int(gl),
        "p_valor": float(p),
    }


def regressao_log(df: pd.DataFrame) -> pd.DataFrame:
    """MQO sobre log(dock-to-stock): cada coeficiente vira efeito percentual (e^β − 1)."""
    X = pd.DataFrame(
        {
            "nao_agendado": (~df.agendado).astype(float),
            "sem_asn": (~df.asn_antecipado).astype(float),
            "divergencia": df.divergencia.astype(float),
            "carga_batida": (df.tipo_carga == "batida").astype(float),
            "carga_mista": (df.tipo_carga == "mista").astype(float),
            "turno_noite": (df.turno_chegada == "noite").astype(float),
            "skus_10": df.skus / 10,
        }
    )
    Xm = np.column_stack([np.ones(len(X)), X.to_numpy()])
    y = np.log(df.dock_to_stock_h.to_numpy())
    beta, *_ = np.linalg.lstsq(Xm, y, rcond=None)
    resid = y - Xm @ beta
    gl = len(y) - Xm.shape[1]
    s2 = resid @ resid / gl
    ep = np.sqrt(np.diag(s2 * np.linalg.inv(Xm.T @ Xm)))
    r2 = 1 - resid.var() / y.var()
    out = pd.DataFrame(
        {
            "coef": beta,
            "efeito_pct": np.exp(beta) - 1,
            "erro_padrao": ep,
            "p_valor": 2 * stats.t.sf(np.abs(beta / ep), gl),
        },
        index=["intercepto", *list(X.columns)],
    )
    out.attrs["r2"] = float(r2)
    return out


# ---------------------------------------------------------------- Melhorar / Controlar
def capabilidade_nao_normal(x: pd.Series, lse: float = LSE_HORAS) -> dict:
    """Ppk pelo método dos percentis (ISO 22514-2 / Clements), adequado a tempos assimétricos.

    Ppk = (LSE − mediana) / (P99,865 − mediana). Também reporta o Ppk "normal", que engana em caudas longas.
    """
    x = x.dropna()
    med, p99 = x.median(), x.quantile(0.99865)
    return {
        "n": len(x),
        "mediana": float(med),
        "p90": float(x.quantile(0.9)),
        "pct_fora_sla": float((x > lse).mean()),
        "ppm_fora_sla": float((x > lse).mean() * 1e6),
        "ppk_percentil": float((lse - med) / (p99 - med)),
        "ppk_normal_enganoso": float((lse - x.mean()) / (3 * x.std(ddof=1))),
    }


def antes_depois(df: pd.DataFrame, y: str = "dock_to_stock_h") -> dict:
    a = df.loc[df.fase == "medir", y]
    b = df.loc[df.fase == "piloto", y]
    return {
        "mediana_antes": float(a.median()),
        "mediana_depois": float(b.median()),
        "p90_antes": float(a.quantile(0.9)),
        "p90_depois": float(b.quantile(0.9)),
        "reducao_p90": float(1 - b.quantile(0.9) / a.quantile(0.9)),
        "mann_whitney_p": float(stats.mannwhitneyu(a, b, alternative="greater").pvalue),
        "levene_p": float(stats.levene(a, b).pvalue),
    }


def serie_diaria_p90(df: pd.DataFrame) -> pd.DataFrame:
    """P90 diário do dock-to-stock, com a fase de cada dia (entrada da carta I-MR por fases)."""
    g = df.groupby(df.chegada.dt.normalize())
    return pd.DataFrame({"p90": g.dock_to_stock_h.quantile(0.9), "fase": g.fase.first()})
