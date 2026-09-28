"""Planejamento do mix de recursos: equilibrar pessoas e recursos materiais sem
sacrificar o resultado financeiro nem os planos futuros.

Modelo de programação linear (HiGHS via scipy) com horizonte semanal. Em cada
semana escolhe:
    H  quadro próprio (operadores)       C  contratações      D  desligamentos
    HE horas extras                      T  horas de temporários
    P  pedidos enviados ao 3PL

e minimiza o custo total sujeito a:
    capacidade  ≥ demanda × (1 + buffer de SLA)
    acurácia ponderada do mix ≥ meta     (qualidade não é variável de ajuste)
    HE ≤ limite × horas do quadro        (saúde / NR-1 / CLT)
    temporários ≤ % das horas totais
    3PL ≤ % da demanda                   (KRI de dependência)
    contratações/semana ≤ capacidade de recrutamento
    quadro final ≥ mínimo estratégico    (plano de expansão do ano seguinte)
    orçamento (opcional)

Os preços-sombra da restrição de capacidade dão o custo marginal de um pedido
extra em cada semana: é o número que mostra ao CFO quanto custa "só mais uma
campanha" na semana da Black Friday.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

import numpy as np
import pandas as pd
from scipy.optimize import linprog

from kpikit.config import ParametrosCapacidade


@dataclass
class Cenario:
    demanda: pd.Series                      # pedidos por semana (índice = semana)
    hc_inicial: float | None = None         # None → quadro que cobre 85% da 1ª semana
    horas_semana: float = 44.0
    absenteismo: float = 0.05
    buffer_sla: float = 0.05
    limite_he: float = 0.15
    limite_temp: float = 0.25
    limite_3pl: float = 0.30
    capacidade_3pl_semana: float | None = None  # None → limite_3pl × pico de demanda
    max_contratacoes_semana: float = 500    # ~70 por CD por semana na rede de 7 CDs
    fator_rampa_novato: float = 0.40        # capacidade perdida na 1ª semana de cada contratado
    custo_contratacao: float = 3_500.0
    custo_desligamento: float = 6_000.0
    acuracia_meta: float = 0.9968
    hc_final_minimo: float | None = None
    orcamento: float | None = None
    params: ParametrosCapacidade = field(default_factory=ParametrosCapacidade)


@dataclass
class Resultado:
    status: str
    plano: pd.DataFrame
    custo_total: float
    custo_por_pedido: float
    acuracia_mix: float
    participacao_3pl: float
    custo_marginal_pedido: pd.Series


VARS = ["H", "C", "D", "HE", "T", "P"]


def otimizar(c: Cenario) -> Resultado:
    p = c.params
    n = len(c.demanda)
    nv = len(VARS) * n
    idx = {v: np.arange(i * n, (i + 1) * n) for i, v in enumerate(VARS)}
    hs = c.horas_semana * (1 - c.absenteismo)          # horas produtivas por operador próprio
    prod = p.produtividade_pedidos_hh
    prod_t = prod * p.fator_produtividade_temp
    acc = p.acuracia
    dem = c.demanda.to_numpy(dtype=float)
    hc0 = c.hc_inicial if c.hc_inicial is not None else 0.85 * dem[0] * (1 + c.buffer_sla) / (prod * hs)
    cap3 = c.capacidade_3pl_semana if c.capacidade_3pl_semana is not None else c.limite_3pl * dem.max()

    custo = np.zeros(nv)
    custo[idx["H"]] = c.horas_semana * p.custo_hh_proprio  # paga-se a hora contratada, não a produtiva
    custo[idx["C"]] = c.custo_contratacao
    custo[idx["D"]] = c.custo_desligamento
    custo[idx["HE"]] = p.custo_hh_extra
    custo[idx["T"]] = p.custo_hh_temporario
    custo[idx["P"]] = p.custo_pedido_3pl

    A_ub, b_ub, nomes = [], [], []

    def linha():
        return np.zeros(nv)

    for t in range(n):
        # Capacidade: -(pedidos próprios + extra + temp + 3PL) ≤ -demanda·(1+buffer)
        r = linha()
        r[idx["H"][t]] = -prod * hs
        r[idx["C"][t]] = prod * hs * c.fator_rampa_novato
        r[idx["HE"][t]] = -prod
        r[idx["T"][t]] = -prod_t
        r[idx["P"][t]] = -1
        A_ub.append(r); b_ub.append(-dem[t] * (1 + c.buffer_sla)); nomes.append(("capacidade", t))
        # Acurácia: Σ pedidos_s · (meta − acc_s) ≤ 0
        r = linha()
        r[idx["H"][t]] = prod * hs * (c.acuracia_meta - acc["proprio"])
        r[idx["HE"][t]] = prod * (c.acuracia_meta - acc["extra"])
        r[idx["T"][t]] = prod_t * (c.acuracia_meta - acc["temporario"])
        r[idx["P"][t]] = c.acuracia_meta - acc["3pl"]
        A_ub.append(r); b_ub.append(0.0); nomes.append(("acuracia", t))
        # Horas extras ≤ limite × horas do quadro
        r = linha(); r[idx["HE"][t]] = 1; r[idx["H"][t]] = -c.limite_he * c.horas_semana
        A_ub.append(r); b_ub.append(0.0); nomes.append(("horas_extras", t))
        # Temporários ≤ limite × horas totais  →  T(1−l) − l·hs·H − l·HE ≤ 0
        r = linha(); r[idx["T"][t]] = 1 - c.limite_temp
        r[idx["H"][t]] = -c.limite_temp * hs; r[idx["HE"][t]] = -c.limite_temp
        A_ub.append(r); b_ub.append(0.0); nomes.append(("temporarios", t))
        # 3PL ≤ limite × demanda
        r = linha(); r[idx["P"][t]] = 1
        A_ub.append(r); b_ub.append(c.limite_3pl * dem[t]); nomes.append(("dependencia_3pl", t))

    if c.hc_final_minimo is not None:
        r = linha(); r[idx["H"][n - 1]] = -1
        A_ub.append(r); b_ub.append(-c.hc_final_minimo); nomes.append(("quadro_final", n - 1))
    if c.orcamento is not None:
        A_ub.append(custo.copy()); b_ub.append(c.orcamento); nomes.append(("orcamento", n - 1))

    # Balanço de quadro: H_t − H_{t−1} − C_t + D_t = 0
    A_eq, b_eq = [], []
    for t in range(n):
        r = linha()
        r[idx["H"][t]] = 1; r[idx["C"][t]] = -1; r[idx["D"][t]] = 1
        if t > 0:
            r[idx["H"][t - 1]] = -1
            A_eq.append(r); b_eq.append(0.0)
        else:
            A_eq.append(r); b_eq.append(hc0)

    limites = []
    for v in VARS:
        for _ in range(n):
            if v == "C":
                limites.append((0, c.max_contratacoes_semana))
            elif v == "P":
                limites.append((0, cap3))
            else:
                limites.append((0, None))

    res = linprog(custo, A_ub=np.array(A_ub), b_ub=np.array(b_ub), A_eq=np.array(A_eq), b_eq=np.array(b_eq),
                  bounds=limites, method="highs")
    if res.status != 0:
        vazio = pd.DataFrame()
        return Resultado("inviavel: " + res.message, vazio, np.nan, np.nan, np.nan, np.nan, pd.Series(dtype=float))

    x = res.x
    plano = pd.DataFrame({v: x[idx[v]] for v in VARS}, index=c.demanda.index)
    plano.columns = ["quadro_proprio", "contratacoes", "desligamentos", "horas_extras",
                     "horas_temporarios", "pedidos_3pl"]
    plano.insert(0, "demanda", dem)
    plano["ped_proprio"] = prod * (plano.quadro_proprio * hs - plano.contratacoes * hs * c.fator_rampa_novato)
    plano["ped_extra"] = prod * plano.horas_extras
    plano["ped_temporario"] = prod_t * plano.horas_temporarios
    fontes = {"ped_proprio": "proprio", "ped_extra": "extra", "ped_temporario": "temporario",
              "pedidos_3pl": "3pl"}
    total_ped = plano[list(fontes)].sum(axis=1)
    plano["acuracia_mix"] = sum(plano[k] * acc[v] for k, v in fontes.items()) / total_ped
    plano["custo"] = [float(custo[[idx[v][t] for v in VARS]] @ x[[idx[v][t] for v in VARS]]) for t in range(n)]

    duais = res.ineqlin.marginals
    cm = pd.Series([-duais[i] for i, (nome, _) in enumerate(nomes) if nome == "capacidade"],
                   index=c.demanda.index, name="custo_marginal_pedido")
    ped = plano[list(fontes)].to_numpy().sum()
    return Resultado(
        status="otimo", plano=plano.round(2), custo_total=float(res.fun),
        custo_por_pedido=float(res.fun / dem.sum()),
        acuracia_mix=float((plano[list(fontes)].mul([acc[v] for v in fontes.values()]).sum().sum()) / ped),
        participacao_3pl=float(plano.pedidos_3pl.sum() / ped), custo_marginal_pedido=cm,
    )


def curva_tradeoff(base: Cenario, parametro: str, valores) -> pd.DataFrame:
    """Reotimiza variando um parâmetro. Mostra o preço de cada escolha de política."""
    linhas = []
    for v in valores:
        r = otimizar(replace(base, **{parametro: v}))
        linhas.append({parametro: v, "status": r.status, "custo_total": r.custo_total,
                       "custo_por_pedido": r.custo_por_pedido, "acuracia_mix": r.acuracia_mix,
                       "participacao_3pl": r.participacao_3pl})
    return pd.DataFrame(linhas)


def demanda_projetada(dados: dict[str, pd.DataFrame], inicio="2025-09-01", fim="2025-12-31",
                      crescimento: float = 0.35) -> pd.Series:
    """Projeção semanal para o ano seguinte: histórico × (1 + crescimento). Pedidos nacionais."""
    dem = dados["fato_demanda"]
    dem = dem[(dem.data >= pd.Timestamp(inicio)) & (dem.data <= pd.Timestamp(fim))]
    semanal = dem.groupby(pd.Grouper(key="data", freq="W-SUN")).pedidos.sum() * (1 + crescimento)
    semanal.index = (semanal.index + pd.DateOffset(years=1)).strftime("%Y-%m-%d")
    semanal.index.name = "semana"
    return semanal.iloc[1:-1]  # descarta semanas parciais
