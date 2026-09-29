"""Marketing: quanto da venda a mídia realmente causa?

1. Marketing Mix Modeling (MMM)   → gerar_serie_mmm · ajustar_mmm · curvas_resposta · otimizar_orcamento
2. Teste de incrementalidade geo  → gerar_teste_geo · estimar_lift · teste_permutacao · poder_do_teste

A série é simulada com parâmetros verdadeiros conhecidos (VERDADE). Assim, dá para verificar se o
método recupera a verdade antes de confiar nele em dados reais. Todos os parâmetros são premissas
de camada D; os fatores de inflação da atribuição de plataforma são ilustrativos.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import lsq_linear, minimize

from kpikit import config as cfg


@dataclass(frozen=True)
class CanalVerdade:
    participacao: float  # fatia do orçamento
    adstock: float  # fração do efeito que "sobra" para a semana seguinte (0 a 1)
    saturacao: float  # meia-saturação, em múltiplos do investimento semanal médio do canal
    roas_incremental: float  # receita causada / investimento, no investimento médio
    inflacao_plataforma: float  # ROAS reportado pela plataforma ÷ ROAS incremental


VERDADE = {
    "Google Search": CanalVerdade(0.34, 0.10, 1.5, 6.0, 1.6),
    "Meta Ads": CanalVerdade(0.30, 0.45, 2.0, 3.5, 1.8),
    "Google PMax": CanalVerdade(0.18, 0.20, 1.0, 2.2, 3.0),
    "TikTok Ads": CanalVerdade(0.10, 0.60, 1.2, 1.5, 3.5),
    "Retail Media": CanalVerdade(0.08, 0.20, 1.5, 5.0, 1.3),
}
CANAIS = list(VERDADE)
INVESTIMENTO_SEMANAL = cfg.INVESTIMENTO_MIDIA_DIA * 7
RECEITA_BASE_SEMANAL = 95_000_000.0
RUIDO_SEMANAL = 0.012  # desvio do ruído, em fração da receita base (choques não explicados)
BREAK_EVEN_ROAS = 1 / cfg.MARGEM_CONTRIBUICAO  # ROAS em que a margem da 1ª compra paga a mídia


# ---------------------------------------------------------------- transformações
def adstock(x: np.ndarray, theta: float) -> np.ndarray:
    """Adstock geométrico: efeito_t = x_t + θ · efeito_{t−1} (a mídia de hoje ainda vende amanhã)."""
    out = np.empty_like(x, dtype=float)
    acumulado = 0.0
    for t, v in enumerate(x):
        acumulado = v + theta * acumulado
        out[t] = acumulado
    return out


def hill(x: np.ndarray, meia_saturacao: float) -> np.ndarray:
    """Saturação (Michaelis-Menten): cada real a mais rende menos que o anterior."""
    return x / (x + meia_saturacao)


# ---------------------------------------------------------------- série simulada
def gerar_serie_mmm(semanas: int = 104, semente: int = 21) -> tuple[pd.DataFrame, dict[str, float]]:
    """Receita semanal = base (tendência + sazonalidade + pico) + Σ contribuição dos canais + ruído.

    Retorna a série e os coeficientes verdadeiros β de cada canal (escala da receita).
    """
    rng = np.random.default_rng(semente)
    datas = pd.date_range("2024-09-30", periods=semanas, freq="W-MON")
    t = np.arange(semanas)
    semana_ano = datas.isocalendar().week.to_numpy()
    pico = np.isin(semana_ano, [47, 48]).astype(float)  # Black Friday / Cyber
    natal = np.isin(semana_ano, [50, 51]).astype(float)
    # Base aditiva: tendência + sazonalidade anual + eventos (a mesma estrutura dos controles do modelo).
    base = RECEITA_BASE_SEMANAL * (
        1 + 0.006 * t + 0.08 * np.sin(2 * np.pi * (semana_ano - 10) / 52) + 0.9 * pico + 0.35 * natal
    )
    df = pd.DataFrame({"semana": datas, "pico": pico, "natal": natal})
    beta = {}
    contrib_total = np.zeros(semanas)
    for canal, v in VERDADE.items():
        medio = INVESTIMENTO_SEMANAL * v.participacao
        # Variação de verba independente por canal (flighting) é o que torna o MMM identificável.
        gasto = medio * rng.lognormal(0, 0.35, semanas) * (1 + 0.8 * pico + 0.3 * natal)
        gasto[rng.random(semanas) < 0.06] *= 0.15  # semanas quase "no escuro"
        k = v.saturacao * medio / (1 - v.adstock)
        # β calibrado para que, no investimento médio em regime, receita causada / gasto = ROAS incremental.
        estado = medio / (1 - v.adstock)
        beta[canal] = v.roas_incremental * medio / hill(np.array([estado]), k)[0]
        contrib = beta[canal] * hill(adstock(gasto, v.adstock), k)
        df[f"gasto_{canal}"] = gasto.round(2)
        df[f"contrib_real_{canal}"] = contrib.round(2)
        df[f"receita_plataforma_{canal}"] = (
            gasto * v.roas_incremental * v.inflacao_plataforma * rng.normal(1, 0.05, semanas)
        ).round(2)
        contrib_total += contrib
    df["receita_base_real"] = base.round(2)
    df["receita"] = base + contrib_total + rng.normal(0, RUIDO_SEMANAL * RECEITA_BASE_SEMANAL, semanas)
    return df, beta


# ---------------------------------------------------------------- MMM
@dataclass
class ModeloMMM:
    theta: dict[str, float]
    k: dict[str, float]
    beta: dict[str, float]
    controles: np.ndarray
    colunas_controle: list[str]
    r2_treino: float
    mape_teste: float
    ajustado: pd.Series


def _controles(df: pd.DataFrame) -> pd.DataFrame:
    t = np.arange(len(df))
    semana_ano = df.semana.dt.isocalendar().week.to_numpy()
    return pd.DataFrame(
        {
            "intercepto": 1.0,
            "tendencia": t / len(df),
            "sen": np.sin(2 * np.pi * semana_ano / 52),
            "cos": np.cos(2 * np.pi * semana_ano / 52),
            "pico": df.pico.to_numpy(),
            "natal": df.natal.to_numpy(),
        },
        index=df.index,
    )


def _matriz(df, theta, k):
    X_c = _controles(df)
    X_m = pd.DataFrame({c: hill(adstock(df[f"gasto_{c}"].to_numpy(), theta[c]), k[c]) for c in CANAIS}, index=df.index)
    return X_c, X_m


def _resolver(X_c, X_m, y):
    """Mínimos quadrados com limites: controles livres, canais com efeito ≥ 0 (mídia não destrói venda)."""
    X = np.column_stack([X_c.to_numpy(), X_m.to_numpy()])
    escala = np.abs(X).max(axis=0)
    escala[escala == 0] = 1
    lb = np.r_[np.full(X_c.shape[1], -np.inf), np.zeros(X_m.shape[1])]
    res = lsq_linear(X / escala, y, bounds=(lb, np.inf))
    return res.x / escala


def ajustar_mmm(
    df: pd.DataFrame,
    semanas_teste: int = 12,
    calibracao: dict[str, float] | None = None,
    grade_theta=(0.0, 0.1, 0.2, 0.3, 0.45, 0.6, 0.75),
    grade_k=(0.5, 1.0, 1.5, 2.0, 3.0),
    rodadas: int = 3,
) -> ModeloMMM:
    """Ajusta adstock (θ) e saturação (k) por busca em grade coordenada, canal a canal.

    Em cada combinação candidata, os coeficientes vêm de mínimos quadrados com limites, e a escolha
    minimiza o erro quadrático na série inteira. O MAPE das últimas `semanas_teste` semanas é
    reportado reajustando só com o passado (validação honesta, na ordem do tempo).

    calibracao: {canal: ROAS medido em experimento}. O canal calibrado tem seu β fixado para
    reproduzir o ROAS do experimento, e os demais são reestimados em torno dele.
    """
    calibracao = calibracao or {}
    y = df.receita.to_numpy()
    n = len(df)
    medio = {c: df[f"gasto_{c}"].mean() for c in CANAIS}
    livres = [c for c in CANAIS if c not in calibracao]

    def ajustar(th, km, mascara):
        k = {c: km[c] * medio[c] / (1 - th[c]) for c in CANAIS}
        X_c, X_m = _matriz(df, th, k)
        fixo = np.zeros(n)
        beta = {}
        for c, roas in calibracao.items():
            beta[c] = roas * df[f"gasto_{c}"].sum() / X_m[c].sum()
            fixo += beta[c] * X_m[c].to_numpy()
        coef = _resolver(X_c[mascara], X_m.loc[mascara, livres], (y - fixo)[mascara])
        beta.update(zip(livres, coef[X_c.shape[1] :], strict=True))
        prev = X_c.to_numpy() @ coef[: X_c.shape[1]] + X_m[livres].to_numpy() @ coef[X_c.shape[1] :] + fixo
        return prev, coef[: X_c.shape[1]], beta, k

    def sse(th, km):
        prev = ajustar(th, km, np.ones(n, bool))[0]
        return float(np.mean((prev - y) ** 2))

    theta = dict.fromkeys(CANAIS, 0.3)
    k_mult = dict.fromkeys(CANAIS, 1.5)
    melhor = sse(theta, k_mult)
    for _ in range(rodadas):
        for c in CANAIS:
            for th in grade_theta:
                for km in grade_k:
                    cand_t, cand_k = {**theta, c: th}, {**k_mult, c: km}
                    e = sse(cand_t, cand_k)
                    if e < melhor - 1e-9:
                        melhor, theta, k_mult = e, cand_t, cand_k
    prev, controles, beta, k = ajustar(theta, k_mult, np.ones(n, bool))
    treino = np.arange(n) < n - semanas_teste
    prev_holdout = ajustar(theta, k_mult, treino)[0]
    mape = float(np.mean(np.abs(prev_holdout[~treino] - y[~treino]) / y[~treino]))
    r2 = 1 - (y - prev).var() / y.var()
    return ModeloMMM(
        theta=theta,
        k=k,
        beta={c: float(beta[c]) for c in CANAIS},
        controles=controles,
        colunas_controle=list(_controles(df).columns),
        r2_treino=float(r2),
        mape_teste=mape,
        ajustado=pd.Series(prev, index=df.index),
    )


def contribuicoes(df: pd.DataFrame, m: ModeloMMM) -> pd.DataFrame:
    """Receita atribuída a cada canal pelo modelo, semana a semana (decomposição)."""
    _, X_m = _matriz(df, m.theta, m.k)
    return pd.DataFrame({c: X_m[c] * m.beta[c] for c in CANAIS}, index=df.index)


def comparar_roas(df: pd.DataFrame, m: ModeloMMM) -> pd.DataFrame:
    """ROAS da plataforma × ROAS incremental estimado (MMM) × verdade da simulação."""
    contrib = contribuicoes(df, m)
    linhas = []
    for c in CANAIS:
        gasto = df[f"gasto_{c}"].sum()
        linhas.append(
            {
                "canal": c,
                "investimento": gasto,
                "roas_plataforma": df[f"receita_plataforma_{c}"].sum() / gasto,
                "roas_incremental_mmm": contrib[c].sum() / gasto,
                "roas_incremental_real": df[f"contrib_real_{c}"].sum() / gasto,
            }
        )
    out = pd.DataFrame(linhas).set_index("canal")
    out["paga_1a_compra"] = out.roas_incremental_mmm >= BREAK_EVEN_ROAS
    return out


def resposta_regime(gasto_semanal: np.ndarray | float, canal: str, m: ModeloMMM) -> np.ndarray:
    """Receita semanal causada por um gasto semanal constante, em regime (adstock estabilizado)."""
    x = np.asarray(gasto_semanal, dtype=float) / (1 - m.theta[canal])
    return m.beta[canal] * hill(x, m.k[canal])


def roas_marginal(gasto_semanal: float, canal: str, m: ModeloMMM, delta: float = 0.01) -> float:
    """Receita do próximo real investido (derivada numérica da curva de resposta)."""
    g = max(gasto_semanal, 1.0)
    return float((resposta_regime(g * (1 + delta), canal, m) - resposta_regime(g, canal, m)) / (g * delta))


def curvas_resposta(
    df: pd.DataFrame, m: ModeloMMM, multiplos: tuple[float, ...] = tuple(i / 10 for i in range(31))
) -> pd.DataFrame:
    linhas = []
    for c in CANAIS:
        medio = df[f"gasto_{c}"].mean()
        for mult in multiplos:
            linhas.append(
                {
                    "canal": c,
                    "multiplo_do_atual": mult,
                    "gasto_semanal": mult * medio,
                    "receita_incremental": float(resposta_regime(mult * medio, c, m)),
                    "roas_marginal": roas_marginal(mult * medio, c, m) if mult > 0 else np.nan,
                }
            )
    return pd.DataFrame(linhas)


def otimizar_orcamento(
    df: pd.DataFrame, m: ModeloMMM, orcamento_semanal: float | None = None, limites=(0.5, 2.0)
) -> pd.DataFrame:
    """Realoca a verba para maximizar a receita incremental, com guarda-corpos por canal.

    limites: fração mínima e máxima do gasto atual de cada canal (mudanças bruscas são arriscadas:
    o modelo só "conhece" a faixa de gasto que observou).
    """
    atual = np.array([df[f"gasto_{c}"].mean() for c in CANAIS])
    total = orcamento_semanal or atual.sum()

    def neg_receita(x):
        return -sum(float(resposta_regime(x[i], c, m)) for i, c in enumerate(CANAIS))

    res = minimize(
        neg_receita,
        atual * total / atual.sum(),
        method="SLSQP",
        bounds=[(limites[0] * a, limites[1] * a) for a in atual],
        constraints=[{"type": "eq", "fun": lambda x: x.sum() - total}],
    )
    out = pd.DataFrame({"gasto_atual": atual, "gasto_otimo": res.x}, index=CANAIS)
    out["variacao"] = out.gasto_otimo / out.gasto_atual - 1
    out["receita_atual"] = [float(resposta_regime(a, c, m)) for a, c in zip(atual, CANAIS, strict=True)]
    out["receita_otima"] = [float(resposta_regime(g, c, m)) for g, c in zip(res.x, CANAIS, strict=True)]
    out["roas_marginal_otimo"] = [roas_marginal(g, c, m) for g, c in zip(res.x, CANAIS, strict=True)]
    return out


def receita_real_regime(gastos: pd.Series, beta_real: dict[str, float]) -> float:
    """Receita semanal que a alocação realmente causaria, pela verdade da simulação (só para validar)."""
    total = 0.0
    for c, g in gastos.items():
        v = VERDADE[c]
        medio = INVESTIMENTO_SEMANAL * v.participacao
        k = v.saturacao * medio / (1 - v.adstock)
        total += beta_real[c] * float(hill(np.array([g / (1 - v.adstock)]), k)[0])
    return total


def erro_roas(tabela: pd.DataFrame) -> float:
    """Erro absoluto médio do ROAS estimado, ponderado pelo investimento (o erro que custa dinheiro)."""
    erro = (tabela.roas_incremental_mmm - tabela.roas_incremental_real).abs() / tabela.roas_incremental_real
    return float((erro * tabela.investimento).sum() / tabela.investimento.sum())


# ---------------------------------------------------------------- teste geo
def gerar_teste_geo(
    n_geos: int = 30,
    semanas_pre: int = 8,
    semanas_teste: int = 6,
    variacao_gasto_semanal: float = -70_000.0,
    iroas_real: float = VERDADE["Meta Ads"].roas_incremental,
    semente: int = 5,
) -> pd.DataFrame:
    """Painel geo × semana. Metade das praças (sorteadas) muda a verba de Meta no período de teste.

    O padrão é um teste de desligamento (holdout geográfico): as praças tratadas param de investir
    em Meta. A venda perdida ÷ verba economizada mede o ROAS incremental médio do canal, que é o
    número comparável ao MMM. Com variação positiva, o teste mede o retorno marginal de um aumento.
    iroas_real: receita incremental verdadeira por real (o que o teste deve recuperar).
    """
    rng = np.random.default_rng(semente)
    tamanho = rng.lognormal(np.log(1_200_000), 0.6, n_geos)  # receita semanal típica da praça
    tratadas = rng.permutation(n_geos) < n_geos // 2
    semanas = semanas_pre + semanas_teste
    choque_semana = rng.normal(0, 0.03, semanas)  # choques comuns (clima, calendário)
    linhas = []
    for g in range(n_geos):
        nivel = tamanho[g] * (1 + rng.normal(0, 0.02, semanas).cumsum() * 0.3)
        for s in range(semanas):
            teste = s >= semanas_pre
            extra = variacao_gasto_semanal * tamanho[g] / tamanho.mean() if (tratadas[g] and teste) else 0.0
            receita = nivel[s] * (1 + choque_semana[s]) * rng.normal(1, 0.04) + iroas_real * extra
            linhas.append(
                {
                    "geo": f"G{g + 1:02d}",
                    "semana": s,
                    "tratada": bool(tratadas[g]),
                    "periodo_teste": teste,
                    "gasto_extra": extra,  # negativo = verba retirada
                    "receita": receita,
                }
            )
    return pd.DataFrame(linhas)


def estimar_lift(painel: pd.DataFrame) -> dict[str, float]:
    """Diferença-em-diferenças por praça: (teste − pré) das tratadas menos (teste − pré) das controle.

    Comparar cada praça com ela mesma remove diferenças de tamanho; comparar com o grupo controle
    remove choques comuns a todas (clima, feriado, sazonalidade).
    """
    por_geo = painel.groupby(["geo", "tratada", "periodo_teste"]).receita.mean().unstack()
    delta = (por_geo[True] - por_geo[False]).reset_index().rename(columns={0: "delta"})
    delta.columns = ["geo", "tratada", "delta"]
    d_trat = delta.loc[delta.tratada, "delta"].mean()
    d_ctrl = delta.loc[~delta.tratada, "delta"].mean()
    semanas_teste = painel.loc[painel.periodo_teste, "semana"].nunique()
    n_trat = delta.tratada.sum()
    lift_semanal_por_geo = d_trat - d_ctrl
    receita_incremental = lift_semanal_por_geo * n_trat * semanas_teste
    gasto_extra = painel.loc[painel.tratada & painel.periodo_teste, "gasto_extra"].sum()
    return {
        "receita_incremental": float(receita_incremental),
        "gasto_extra": float(gasto_extra),
        "iroas": float(receita_incremental / gasto_extra) if gasto_extra else np.nan,
        "lift_pct": float(lift_semanal_por_geo / painel.loc[painel.tratada & ~painel.periodo_teste, "receita"].mean()),
    }


def teste_permutacao(painel: pd.DataFrame, n: int = 2_000, semente: int = 0) -> dict[str, float]:
    """Sorteia de novo quem é 'tratada' milhares de vezes: qual a chance de um lift desse tamanho
    aparecer por acaso? Não supõe normalidade, e é o teste certo para poucas praças."""
    rng = np.random.default_rng(semente)
    por_geo = painel.groupby(["geo", "periodo_teste"]).receita.mean().unstack()
    delta = (por_geo[True] - por_geo[False]).to_numpy()
    tratada = painel.groupby("geo").tratada.first().loc[por_geo.index].to_numpy()
    observado = delta[tratada].mean() - delta[~tratada].mean()
    nulos = np.empty(n)
    for i in range(n):
        p = rng.permutation(tratada)
        nulos[i] = delta[p].mean() - delta[~p].mean()
    semanas_teste = painel.loc[painel.periodo_teste, "semana"].nunique()
    gasto = painel.loc[painel.tratada & painel.periodo_teste, "gasto_extra"].sum()
    escala = tratada.sum() * semanas_teste / gasto
    lo, hi = np.percentile(nulos, [2.5, 97.5])
    # IC aproximado: variação do acaso em torno do efeito observado (ordenado, pois a escala pode ser negativa).
    ic = sorted([(observado - hi) * escala, (observado - lo) * escala])
    return {
        "p_valor": float((np.abs(nulos) >= abs(observado)).mean()),
        "iroas": float(observado * escala),
        "iroas_ic_inf": float(ic[0]),
        "iroas_ic_sup": float(ic[1]),
    }


def poder_do_teste(
    iroas_real: float = VERDADE["Meta Ads"].roas_incremental,
    geos=(10, 20, 30, 40),
    semanas=(4, 6, 8),
    simulacoes: int = 120,
    alfa: float = 0.05,
) -> pd.DataFrame:
    """Probabilidade de detectar o efeito (p < α), por número de praças e duração do teste."""
    linhas = []
    for g in geos:
        for s in semanas:
            acertos = 0
            for sim in range(simulacoes):
                painel = gerar_teste_geo(n_geos=g, semanas_teste=s, iroas_real=iroas_real, semente=1_000 + sim)
                d = painel.groupby(["geo", "tratada", "periodo_teste"]).receita.mean().unstack()
                delta = (d[True] - d[False]).reset_index()
                a = delta.loc[delta.tratada, 0]
                b = delta.loc[~delta.tratada, 0]
                acertos += stats.ttest_ind(a, b, equal_var=False).pvalue < alfa
            linhas.append({"praças": g, "semanas": s, "poder": acertos / simulacoes})
    return pd.DataFrame(linhas).pivot(index="praças", columns="semanas", values="poder")
