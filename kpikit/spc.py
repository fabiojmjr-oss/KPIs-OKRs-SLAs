"""Controle Estatístico de Processo (CEP) e capability.

Ponto de atenção para dados logísticos: proporções com denominador enorme
(100 mil pedidos/dia) fazem a carta p clássica ter limites estreitíssimos, e
quase todo ponto parece "fora de controle" (sobredispersão). A carta p' de
Laney corrige isso usando a variação real entre subgrupos. Usar a carta p pura
nesses casos gera caça a causas especiais inexistentes.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

D2 = 1.128  # constante para amplitude móvel de n=2
D4 = 3.267


def carta_imr(x: pd.Series) -> pd.DataFrame:
    """Carta de valores individuais e amplitude móvel (I-MR)."""
    x = x.dropna().astype(float)
    mr = x.diff().abs()
    mr_bar = mr.mean()
    sigma = mr_bar / D2
    centro = x.mean()
    df = pd.DataFrame(
        {
            "valor": x,
            "centro": centro,
            "lsc": centro + 3 * sigma,
            "lic": centro - 3 * sigma,
            "mr": mr,
            "mr_lsc": D4 * mr_bar,
        }
    )
    df.attrs["sigma"] = sigma
    return df


def carta_p(defeitos: pd.Series, n: pd.Series, laney: bool = True) -> pd.DataFrame:
    """Carta p (ou p' de Laney, padrão) para proporção de não conformes com n variável."""
    p = defeitos / n
    p_bar = defeitos.sum() / n.sum()
    sigma_p = np.sqrt(p_bar * (1 - p_bar) / n)
    fator = 1.0
    if laney:
        z = (p - p_bar) / sigma_p
        fator = (z.diff().abs().mean()) / D2
    lsc = (p_bar + 3 * sigma_p * fator).clip(upper=1)
    lic = (p_bar - 3 * sigma_p * fator).clip(lower=0)
    df = pd.DataFrame({"valor": p, "centro": p_bar, "lsc": lsc, "lic": lic, "n": n})
    df.attrs["sigma_z"] = fator
    return df


def regras_nelson(carta: pd.DataFrame) -> pd.DataFrame:
    """Aplica regras de Nelson 1, 2, 3 e 5 sobre uma carta (colunas valor/centro/lsc/lic).

    1: ponto além de 3σ · 2: 9 pontos seguidos do mesmo lado da média
    3: 6 pontos seguidos subindo ou descendo · 5: 2 de 3 pontos além de 2σ do mesmo lado
    """
    v, c = carta["valor"], carta["centro"]
    sigma = (carta["lsc"] - c) / 3
    lado = np.sign(v - c)
    r1 = (v > carta["lsc"]) | (v < carta["lic"])
    r2 = lado.rolling(9).apply(lambda s: abs(s.sum()) == 9, raw=True).fillna(0).astype(bool)
    delta = np.sign(v.diff())
    r3 = delta.rolling(6).apply(lambda s: abs(s.sum()) == 6, raw=True).fillna(0).astype(bool)
    acima2 = (v > c + 2 * sigma).astype(int).rolling(3).sum() >= 2
    abaixo2 = (v < c - 2 * sigma).astype(int).rolling(3).sum() >= 2
    r5 = acima2 | abaixo2
    out = pd.DataFrame({"regra_1": r1, "regra_2": r2, "regra_3": r3, "regra_5": r5}, index=carta.index)
    out["algum_sinal"] = out.any(axis=1)
    return out


def capabilidade(x: pd.Series, lie: float | None = None, lse: float | None = None) -> dict[str, float]:
    """Cp, Cpk (σ de curto prazo via MR) e Pp, Ppk (σ global)."""
    x = x.dropna().astype(float)
    mu = x.mean()
    s_curto = x.diff().abs().mean() / D2
    s_longo = x.std(ddof=1)

    def indices(s: float) -> tuple[float, float]:
        lados = []
        if lse is not None:
            lados.append((lse - mu) / (3 * s))
        if lie is not None:
            lados.append((mu - lie) / (3 * s))
        p = (lse - lie) / (6 * s) if lse is not None and lie is not None else np.nan
        return p, min(lados)

    cp, cpk = indices(s_curto)
    pp, ppk = indices(s_longo)
    fora = ((x > lse).sum() if lse is not None else 0) + ((x < lie).sum() if lie is not None else 0)
    return {
        "media": mu,
        "sigma_curto": s_curto,
        "sigma_longo": s_longo,
        "Cp": cp,
        "Cpk": cpk,
        "Pp": pp,
        "Ppk": ppk,
        "pct_fora_spec_observado": fora / len(x),
    }


def dpmo(defeitos: float, unidades: float, oportunidades: float = 1) -> float:
    return defeitos / (unidades * oportunidades) * 1e6


def nivel_sigma(dpmo_valor: float, deslocamento: float = 1.5) -> float:
    """Nível sigma pela convenção de deslocamento de 1,5σ (3,4 DPMO ≈ 6σ)."""
    return float(stats.norm.ppf(1 - dpmo_valor / 1e6) + deslocamento)


def plotar(carta: pd.DataFrame, titulo: str, sinais: pd.Series | None = None, ax=None, formato_pct=False):
    """Plota a carta com matplotlib; destaca pontos com sinal de causa especial."""
    import matplotlib.pyplot as plt
    from matplotlib.ticker import PercentFormatter

    if ax is None:
        _, ax = plt.subplots(figsize=(11, 3.6))
    ax.plot(carta.index, carta["valor"], color="#3b6ea5", lw=1.2, marker="o", ms=2.5, label="valor")
    ax.plot(carta.index, carta["centro"], color="#555", lw=1, label="média")
    ax.plot(carta.index, carta["lsc"], color="#c0392b", lw=1, ls="--", label="LSC / LIC")
    ax.plot(carta.index, carta["lic"], color="#c0392b", lw=1, ls="--")
    if sinais is not None and sinais.any():
        pts = carta.loc[sinais, "valor"]
        ax.scatter(pts.index, pts, color="#c0392b", zorder=5, s=28, label="sinal (Nelson)")
    if formato_pct:
        ax.yaxis.set_major_formatter(PercentFormatter(1.0, decimals=1))
    ax.set_title(titulo, loc="left", fontsize=11)
    ax.grid(alpha=0.25)
    ax.legend(loc="lower left", fontsize=8, ncol=4, frameon=False)
    return ax
