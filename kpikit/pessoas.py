"""Força de trabalho: absenteísmo, sobrevivência de contratados e escala 6x1.

Três perguntas que conectam RH à capacidade operacional:
1. Quantos vão faltar amanhã?      → previsao_absenteismo (regressão com calendário, com backtest)
2. Quem vai sair nos 90 primeiros dias e por quê? → kaplan_meier, logrank, regressao_logistica
3. Quantas pessoas escalar, e com que folgas?     → escala_6x1 (programação inteira)
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import Bounds, LinearConstraint, milp

DIAS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


# ---------------------------------------------------------------- 1. Absenteísmo
def _matriz_calendario(df: pd.DataFrame, cal: pd.DataFrame) -> pd.DataFrame:
    x = df[["data", "unidade_id"]].merge(cal[["data", "dia_semana", "mes", "mult_evento"]], on="data", how="left")
    pos_pico = cal.set_index("data").mult_evento
    pos_pico = ((pos_pico.shift(1, fill_value=1) > 1.5) & (pos_pico <= 1.5)).rolling(3, min_periods=1).max()
    x["pos_pico"] = x.data.map(pos_pico).astype(float)
    dummies = pd.get_dummies(x[["dia_semana", "mes", "unidade_id"]].astype(str), drop_first=True, dtype=float)
    return pd.concat([pd.Series(1.0, index=x.index, name="intercepto"), dummies, x[["pos_pico"]]], axis=1)


def previsao_absenteismo(dados: dict[str, pd.DataFrame], corte: str = "2026-04-01") -> tuple[pd.DataFrame, dict]:
    """Regressão linear (MQO) com dia da semana, mês, unidade e ressaca pós-pico.

    Treina até `corte` e testa depois. Compara com a previsão ingênua (mesmo dia da semana
    anterior), que é a régua mínima que qualquer modelo precisa bater.
    """
    df = dados["fato_cd"].dropna(subset=["absenteismo"]).sort_values(["unidade_id", "data"]).reset_index(drop=True)
    X = _matriz_calendario(df, dados["dim_calendario"])
    y = df.absenteismo.to_numpy()
    treino = (df.data < pd.Timestamp(corte)).to_numpy()
    coef, *_ = np.linalg.lstsq(X[treino].to_numpy(), y[treino], rcond=None)
    df["previsto"] = X.to_numpy() @ coef
    df["ingenuo"] = df.groupby("unidade_id").absenteismo.shift(7)
    teste = df[~treino].dropna(subset=["ingenuo"])
    metricas = {
        "mae_modelo_pp": float((teste.absenteismo - teste.previsto).abs().mean() * 100),
        "mae_ingenuo_pp": float((teste.absenteismo - teste.ingenuo).abs().mean() * 100),
        "dias_teste": int(teste.data.nunique()),
    }
    metricas["ganho_vs_ingenuo"] = 1 - metricas["mae_modelo_pp"] / metricas["mae_ingenuo_pp"]
    efeitos = pd.Series(coef, index=X.columns)
    # Dia da semana 0 (segunda) é a referência da codificação; comparamos com a média dos demais dias.
    metricas["segunda_vs_media_pp"] = float(-efeitos.filter(like="dia_semana_").mean() * 100)
    return df.assign(amostra=np.where(treino, "treino", "teste")), metricas


# ---------------------------------------------------------------- 2. Sobrevivência
def base_sobrevivencia(colab: pd.DataFrame, fim: str | pd.Timestamp) -> pd.DataFrame:
    """Duração (dias) até a saída; quem ainda está ativo entra como censurado (evento = 0)."""
    fim = pd.Timestamp(fim)
    saida = colab.data_desligamento.fillna(fim)
    out = colab.copy()
    out["dias"] = (saida - colab.data_admissao).dt.days.clip(lower=0)
    out["evento"] = colab.data_desligamento.notna().astype(int)
    return out


def kaplan_meier(dias: pd.Series, evento: pd.Series) -> pd.DataFrame:
    """Estimador de Kaplan-Meier com intervalo de 95% (Greenwood, escala log-log)."""
    df = pd.DataFrame({"t": dias.to_numpy(), "e": evento.to_numpy()})
    tabela = df.groupby("t").agg(saidas=("e", "sum"), n=("e", "size")).sort_index()
    tabela["em_risco"] = tabela.n[::-1].cumsum()[::-1]
    h = tabela.saidas / tabela.em_risco
    tabela["sobrevivencia"] = (1 - h).cumprod()
    var = (tabela.saidas / (tabela.em_risco * (tabela.em_risco - tabela.saidas)).replace(0, np.nan)).cumsum()
    with np.errstate(divide="ignore", invalid="ignore"):
        loglog = np.log(-np.log(tabela.sobrevivencia))
        se = np.sqrt(var) / np.abs(np.log(tabela.sobrevivencia))
        tabela["ic_inf"] = np.exp(-np.exp(loglog + 1.96 * se))
        tabela["ic_sup"] = np.exp(-np.exp(loglog - 1.96 * se))
    inicio = pd.DataFrame(
        {"saidas": 0, "n": 0, "em_risco": len(df), "sobrevivencia": 1.0, "ic_inf": 1.0, "ic_sup": 1.0},
        index=pd.Index([0], name="t"),
    )
    return pd.concat([inicio, tabela[tabela.index > 0]])


def sobrevivencia_em(km: pd.DataFrame, t: int) -> float:
    return float(km.sobrevivencia[km.index <= t].iloc[-1])


def logrank(dias: pd.Series, evento: pd.Series, grupo: pd.Series) -> dict:
    """Teste log-rank para 2+ grupos: as curvas de sobrevivência são iguais?"""
    df = pd.DataFrame({"t": dias.to_numpy(), "e": evento.to_numpy(), "g": grupo.to_numpy()})
    grupos = sorted(df.g.unique())
    tempos = np.sort(df.loc[df.e == 1, "t"].unique())
    obs = np.zeros(len(grupos))
    esp = np.zeros(len(grupos))
    V = np.zeros((len(grupos), len(grupos)))
    t_arr, e_arr, g_arr = df.t.to_numpy(), df.e.to_numpy(), df.g.to_numpy()
    for t in tempos:
        em_risco = t_arr >= t
        n = em_risco.sum()
        d = ((t_arr == t) & (e_arr == 1)).sum()
        if n < 2:
            continue
        n_g = np.array([(em_risco & (g_arr == g)).sum() for g in grupos])
        d_g = np.array([((t_arr == t) & (e_arr == 1) & (g_arr == g)).sum() for g in grupos])
        obs += d_g
        esp += d * n_g / n
        fator = d * (n - d) / (n - 1) / n
        V += fator * (np.diag(n_g) - np.outer(n_g, n_g) / n)
    k = len(grupos) - 1
    diff = (obs - esp)[:k]
    qui2 = float(diff @ np.linalg.pinv(V[:k, :k]) @ diff)
    return {
        "qui2": qui2,
        "gl": k,
        "p_valor": float(stats.chi2.sf(qui2, k)),
        "observado": dict(zip(grupos, obs.astype(int), strict=True)),
        "esperado": dict(zip(grupos, esp.round(1), strict=True)),
    }


def regressao_logistica(X: pd.DataFrame, y: pd.Series, iteracoes: int = 50) -> pd.DataFrame:
    """Regressão logística por Newton-Raphson. Retorna coeficientes, razão de chances, IC 95% e p-valor."""
    Xm = np.column_stack([np.ones(len(X)), X.to_numpy(dtype=float)])
    yv = y.to_numpy(dtype=float)
    beta = np.zeros(Xm.shape[1])
    for _ in range(iteracoes):
        p = 1 / (1 + np.exp(-Xm @ beta))
        W = p * (1 - p)
        H = Xm.T @ (Xm * W[:, None])
        passo = np.linalg.solve(H, Xm.T @ (yv - p))
        beta += passo
        if np.abs(passo).max() < 1e-8:
            break
    ep = np.sqrt(np.diag(np.linalg.inv(H)))
    z = beta / ep
    nomes = ["intercepto", *list(X.columns)]
    return pd.DataFrame(
        {
            "coef": beta,
            "erro_padrao": ep,
            "razao_chances": np.exp(beta),
            "rc_ic_inf": np.exp(beta - 1.96 * ep),
            "rc_ic_sup": np.exp(beta + 1.96 * ep),
            "p_valor": 2 * stats.norm.sf(np.abs(z)),
        },
        index=nomes,
    )


def matriz_risco_saida(colab: pd.DataFrame, fim) -> tuple[pd.DataFrame, pd.Series]:
    """Variáveis explicativas e alvo (saiu em < 90 dias) só para quem já completou 90 dias de observação."""
    maduros = colab[colab.data_admissao + pd.Timedelta(days=90) <= pd.Timestamp(fim)].copy()
    y = ((maduros.data_desligamento - maduros.data_admissao).dt.days < 90).astype(int)
    X = pd.DataFrame(
        {
            "turno_noite": (maduros.turno == "noite").astype(int),
            "distancia_10km": (maduros.distancia_km - 9) / 10,
            "canal_agencia": (maduros.canal_recrutamento == "agencia").astype(int),
            "canal_indicacao": (maduros.canal_recrutamento == "indicacao").astype(int),
            "unidade_3pl": (maduros.modelo == "3PL").astype(int),
            "admitido_em_pico": maduros.admitido_em_pico.astype(int),
            "com_buddy": maduros.com_buddy.astype(int),
        },
        index=maduros.index,
    )
    return X, y


# ---------------------------------------------------------------- 3. Escala
def necessidade_semanal(
    dados: dict[str, pd.DataFrame],
    unidade: str,
    inicio: str,
    fim: str,
    produtividade: float = 7.5,
    horas_turno: float = 8.0,
    percentil: float = 0.85,
) -> pd.Series:
    """Operadores presentes necessários por dia da semana (percentil da demanda, não a média)."""
    df = dados["fato_cd"].query("unidade_id == @unidade and pedidos > 0")
    df = df[(df.data >= pd.Timestamp(inicio)) & (df.data <= pd.Timestamp(fim))]
    cal = dados["dim_calendario"].set_index("data")
    df = df[df.data.map(cal.mult_evento) <= 1.0]  # escala-base; pico tem plano próprio
    ped = df.groupby(df.data.dt.dayofweek).pedidos.quantile(percentil)
    nec = np.ceil(ped / (produtividade * horas_turno)).reindex(range(7)).rename(index=dict(enumerate(DIAS)))
    nec.index.name = "dia"
    return nec


@dataclass
class ResultadoEscala:
    quadro: int
    folgas_por_dia: pd.Series  # quantos folgam em cada dia
    cobertura: pd.DataFrame  # necessidade × presentes esperados
    quadro_ingenuo: int
    horas_ociosas_pct: float


def escala_6x1(necessidade: pd.Series, absenteismo: pd.Series, folga_domingo_min: float = 0.0) -> ResultadoEscala:
    """Programação inteira: quantas pessoas folgam em cada dia (regime 6x1) para cobrir a necessidade.

    x_j = nº de operadores com folga no dia j. Presentes no dia d = Σ_{j≠d} x_j.
    Restrição: presentes × (1 − absenteísmo_d) ≥ necessidade_d. Objetivo: mínimo quadro total.
    folga_domingo_min: fração mínima do quadro com folga no domingo (política ou acordo coletivo).
    """
    nec = necessidade.to_numpy(dtype=float)
    ab = absenteismo.to_numpy(dtype=float)
    A = np.ones((7, 7)) - np.eye(7)  # linha d: quem trabalha no dia d
    A_eff = A * (1 - ab)[:, None]
    restricoes = [LinearConstraint(A_eff, lb=nec, ub=np.inf)]
    if folga_domingo_min > 0:
        linha = -folga_domingo_min * np.ones(7)
        linha[6] += 1  # x_dom − f·Σx ≥ 0
        restricoes.append(LinearConstraint(linha[None, :], lb=0, ub=np.inf))
    res = milp(c=np.ones(7), constraints=restricoes, integrality=np.ones(7), bounds=Bounds(0, np.inf))
    if not res.success:
        raise ValueError(f"Escala inviável: {res.message}")
    x = np.round(res.x).astype(int)
    presentes = A @ x * (1 - ab)
    cobertura = pd.DataFrame(
        {"necessidade": nec, "escalados": A @ x, "presentes_esperados": presentes.round(1), "folga_no_dia": x},
        index=necessidade.index,
    )
    # Régua: quadro plano dimensionado pelo pior dia, sem desenhar folgas.
    ingenuo = int(np.ceil((nec / (1 - ab)).max() * 7 / 6))
    ociosas = float((presentes - nec).sum() / presentes.sum())
    return ResultadoEscala(int(x.sum()), pd.Series(x, index=necessidade.index), cobertura, ingenuo, ociosas)
