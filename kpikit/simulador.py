"""Gera dados sintéticos em star schema para o caso Vértice.

O simulador é causal, não aleatório puro: a demanda (sazonalidade + mídia +
expansão) pressiona a capacidade das unidades, e a utilização degrada o
cut-off, a acurácia e o prazo ao longo da cadeia CD → hub → base. Assim, os
trade-offs discutidos em 00-fundamentos/interdependencias.md aparecem nos dados.

Uso: python -m kpikit.simulador  (grava CSVs em dados/)
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from kpikit import config as cfg
from kpikit.dmaic import gerar_recebimentos

PASTA_DADOS = Path(__file__).resolve().parent.parent / "dados"
FATOR_DIA_SEMANA = np.array([1.15, 1.08, 1.02, 1.00, 0.95, 0.82, 0.78])  # seg..dom
PACOTES_POR_CARRETA = 1_800
DISTANCIA_LINEHAUL_KM = {"SE": 180, "S": 420, "CO": 950, "NE": 1_100, "N": 2_700}
CUSTO_KM_CARRETA = 7.8
PRAZO_48H_BASE = {"SE": 0.74, "S": 0.64, "CO": 0.42, "NE": 0.47, "N": 0.20}


MATURIDADE_PREVIA_DIAS = 730  # unidades das regiões maduras já operam há ~2 anos em jan/2025


def _dias_operando(datas: pd.Series, inicio: pd.Timestamp) -> np.ndarray:
    dias = (datas - inicio).dt.days.to_numpy()
    return dias + MATURIDADE_PREVIA_DIAS if inicio == pd.Timestamp(cfg.INICIO) else dias


def efeito(datas: pd.Series, iniciativa: str, rampa_dias: float = 60.0) -> np.ndarray:
    """Intensidade (0 → 1) do efeito de uma iniciativa, em rampa linear após o início."""
    inicio = pd.Timestamp(cfg.INICIATIVAS[iniciativa][1])
    return np.clip((datas - inicio).dt.days.to_numpy() / rampa_dias, 0, 1)


def _fator_capacidade(cal: pd.DataFrame, regiao_id: str) -> np.ndarray:
    fator = 1 + 0.35 * efeito(cal.data, "capacidade_2026", 90)
    if regiao_id in ("NE", "CO"):
        fator = fator * (1 + 0.30 * efeito(cal.data, "cds_regionais", 90))
    return fator


def _perfil_absenteismo(cal: pd.DataFrame) -> np.ndarray:
    """Padrões sistemáticos de ausência: segunda-feira, sexta, inverno e ressaca pós-pico."""
    dia, mes = cal.dia_semana.to_numpy(), cal.mes.to_numpy()
    pos_pico = (cal.mult_evento.shift(1, fill_value=1) > 1.5) & (cal.mult_evento <= 1.5)
    pos_pico = pos_pico.rolling(3, min_periods=1).max().to_numpy()  # 3 dias após o fim do pico
    return (
        0.015 * (dia == 0) + 0.004 * (dia == 4) + 0.006 * np.isin(mes, [6, 7]) + 0.004 * (mes == 2) + 0.012 * pos_pico
    )


def _reforco_pico(cal: pd.DataFrame, cobertura: float) -> np.ndarray:
    """Capacidade extra planejada para eventos: cobre só parte do aumento de demanda."""
    return 1 + (cal.mult_evento.to_numpy() - 1) * cobertura


def _curva_aprendizagem(dias_operando: np.ndarray, tau: float = 75.0) -> np.ndarray:
    """Eficiência relativa de uma unidade nova: 55% no dia 0 → ~100% em ~5·tau/2."""
    return 0.55 + 0.45 * (1 - np.exp(-np.clip(dias_operando, 0, None) / tau))


def _calendario() -> pd.DataFrame:
    datas = pd.date_range(cfg.INICIO, cfg.FIM, freq="D")
    cal = pd.DataFrame({"data": datas})
    cal["ano"] = cal.data.dt.year
    cal["mes"] = cal.data.dt.month
    cal["semana_iso"] = cal.data.dt.isocalendar().week.astype(int)
    cal["dia_semana"] = cal.data.dt.dayofweek
    cal["trimestre"] = cal.data.dt.quarter
    cal["evento"] = ""
    cal["mult_evento"] = 1.0
    for ini, fim, mult, nome in cfg.EVENTOS:
        faixa = cal.data.between(pd.Timestamp(ini), pd.Timestamp(fim))
        cal.loc[faixa, "evento"] = nome
        cal.loc[faixa, "mult_evento"] = mult
    return cal


def _dim_regiao() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "regiao_id": k,
                "regiao": v["nome"],
                "peso_demanda": v["peso"],
                "data_entrada": pd.Timestamp(v["entrada"]),
                "operacao": "madura" if v["entrada"] == cfg.INICIO else "expansao",
            }
            for k, v in cfg.REGIOES.items()
        ]
    )


def _dim_unidade() -> pd.DataFrame:
    df = pd.DataFrame(cfg.UNIDADES, columns=["unidade_id", "tipo", "regiao_id", "modelo", "capacidade_dia"])
    entrada = {k: pd.Timestamp(v["entrada"]) for k, v in cfg.REGIOES.items()}
    df["data_inicio"] = df.regiao_id.map(entrada)
    return df


def _demanda(cal: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    linhas = []
    t = (cal.data - pd.Timestamp(cfg.INICIO)).dt.days.to_numpy()
    crescimento = (1 + cfg.CRESCIMENTO_ANUAL) ** (t / 365)
    for rid, reg in cfg.REGIOES.items():
        dias_ativos = (cal.data - pd.Timestamp(reg["entrada"])).dt.days.to_numpy()
        ativo = dias_ativos >= 0
        # Nova região: conhecimento de marca e sortimento local levam meses para maturar.
        rampa = 1 - 0.65 * np.exp(-np.clip(dias_ativos, 0, None) / 90)
        maturidade = np.where(ativo, 1.0 if reg["entrada"] == cfg.INICIO else rampa, 0)
        ruido = rng.normal(1, 0.035, len(cal))
        pedidos = (
            cfg.PEDIDOS_DIA_BASE
            * reg["peso"]
            * crescimento
            * maturidade
            * FATOR_DIA_SEMANA[cal.dia_semana]
            * cal.mult_evento.to_numpy()
            * ruido
        )
        linhas.append(
            pd.DataFrame(
                {
                    "data": cal.data,
                    "regiao_id": rid,
                    "pedidos": np.round(pedidos).astype(int),
                }
            )
        )
    dem = pd.concat(linhas, ignore_index=True)
    dem["receita"] = dem.pedidos * cfg.TICKET_MEDIO * rng.normal(1, 0.02, len(dem))
    return dem


def _midia(cal: pd.DataFrame, demanda: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    pedidos_dia = demanda.groupby("data").pedidos.sum().reindex(cal.data).to_numpy()
    # Picos recebem mais investimento, mas com retorno marginal decrescente.
    mult_invest = 1 + (cal.mult_evento.to_numpy() - 1) * 1.25
    linhas = []
    for canal, (share, cpm, ctr, conv, inflacao) in cfg.CANAIS_MIDIA.items():
        invest = cfg.INVESTIMENTO_MIDIA_DIA * share * mult_invest * rng.normal(1, 0.05, len(cal))
        impressoes = invest / cpm * 1000
        cliques = impressoes * ctr * rng.normal(1, 0.06, len(cal))
        poas = efeito(cal.data, "midia_poas", 90)
        # Realocação para campanhas incrementais: mais conversão real e margem por real investido.
        conversoes_reais = np.minimum(cliques * conv * (1 + 0.10 * poas), pedidos_dia * share * 0.45)
        conversoes_plat = conversoes_reais * inflacao * rng.normal(1, 0.05, len(cal))
        margem_canal = cfg.MARGEM_CONTRIBUICAO * (1 + 0.12 * poas) * rng.normal(1, 0.08, len(cal))
        linhas.append(
            pd.DataFrame(
                {
                    "data": cal.data,
                    "canal": canal,
                    "investimento": invest.round(2),
                    "impressoes": impressoes.round().astype(int),
                    "cliques": cliques.round().astype(int),
                    "conversoes_atribuidas": conversoes_plat.round().astype(int),
                    "receita_atribuida": (conversoes_plat * cfg.TICKET_MEDIO).round(2),
                    "lucro_bruto_atribuido": (conversoes_plat * cfg.TICKET_MEDIO * margem_canal).round(2),
                    "novos_clientes": (conversoes_reais * 0.42).round().astype(int),
                }
            )
        )
    return pd.concat(linhas, ignore_index=True)


def _cds(cal, demanda, unidades, rng):
    linhas = []
    cds = unidades[unidades.tipo == "CD"]
    for rid in cfg.REGIOES:
        cds_reg = cds[cds.regiao_id == rid]
        dem_reg = demanda[demanda.regiao_id == rid].set_index("data").pedidos.reindex(cal.data).to_numpy()
        for _, cd in cds_reg.iterrows():
            share = cd.capacidade_dia / cds_reg.capacidade_dia.sum()
            pedidos = np.round(dem_reg * share).astype(int)
            dias_op = _dias_operando(cal.data, cd.data_inicio)
            ativo = dias_op >= 0
            aprend = _curva_aprendizagem(dias_op)
            e_3pl = cd.modelo == "3PL"
            # Plano de pico: temporários cobrem parte do aumento; unidades novas cobrem menos.
            cobertura = np.where(dias_op > 180, 0.85, 0.60)
            reforco = 1 + (cal.mult_evento.to_numpy() - 1) * cobertura
            absent = np.clip(
                rng.normal(0.045, 0.008, len(cal)) + _perfil_absenteismo(cal) + 0.01 * (rid in ("NE", "N")), 0.01, 0.15
            )
            wms = efeito(cal.data, "wms_scanner") * (not e_3pl)
            cap_efetiva = (
                cd.capacidade_dia * _fator_capacidade(cal, rid) * aprend * reforco * (1 - absent) / (1 - 0.045)
            )
            util = np.where(ativo, pedidos / cap_efetiva, 0)
            sobrecarga = np.clip(util - 0.88, 0, None)

            cutoff = (
                0.992 - 0.42 * sobrecarga**1.15 - 0.03 * (1 - aprend) - 0.006 * e_3pl + rng.normal(0, 0.004, len(cal))
            )
            cutoff = np.clip(cutoff, 0.55, 0.999)
            linhas_sep = np.round(pedidos * rng.normal(1.9, 0.05, len(cal))).astype(int)
            acuracia = (
                0.99725
                - 0.0012 * e_3pl
                - 0.0025 * np.clip(util - 1, 0, None)
                - 0.004 * (1 - aprend)
                - 0.0015 * (cal.mult_evento.to_numpy() > 1.5)
                + 0.0006 * wms
                + rng.normal(0, 0.00035, len(cal))
            )
            acuracia = np.clip(acuracia, 0.97, 0.9999)
            prod = cfg.ParametrosCapacidade().produtividade_pedidos_hh * aprend * (1 - 0.08 * (util > 1))
            hh = np.where(ativo, pedidos / prod, 0)
            horas_extra = hh * np.clip(util - 0.92, 0, 0.35) * 0.6
            custo = np.where(e_3pl, pedidos * 7.4, hh * 38 + horas_extra * 19)
            d2s = np.clip(
                4.5 + 14 * sobrecarga + 7 * (1 - aprend) + 1.2 * e_3pl - 2.0 * wms + rng.gamma(2, 0.6, len(cal)), 2, 72
            )
            if cd.unidade_id == "CD-AM1":  # resultado do projeto DMAIC (ver kpikit/dmaic.py)
                d2s = d2s * (1 - 0.45 * efeito(cal.data, "dmaic_am1", 30))
            linhas.append(
                pd.DataFrame(
                    {
                        "data": cal.data,
                        "unidade_id": cd.unidade_id,
                        "pedidos": pedidos * ativo,
                        "pedidos_expedidos_cutoff": np.round(pedidos * cutoff * ativo).astype(int),
                        "linhas_separadas": linhas_sep * ativo,
                        "linhas_com_erro": np.round(linhas_sep * (1 - acuracia) * ativo).astype(int),
                        "horas_homem": hh.round(1),
                        "horas_extra": horas_extra.round(1),
                        "absenteismo": np.where(ativo, absent, np.nan).round(4),
                        "utilizacao": util.round(3),
                        "dock_to_stock_p90_h": np.where(ativo, d2s, np.nan).round(2),
                        "custo_operacao": custo.round(2) * ativo,
                    }
                )
            )
    return pd.concat(linhas, ignore_index=True)


def _linehaul_hubs(cal, cds, unidades, rng):
    viagens_l, hubs_l = [], []
    cd_reg = cds.merge(unidades[["unidade_id", "regiao_id"]], on="unidade_id")
    cut = (
        cd_reg.groupby(["data", "regiao_id"])
        .agg(pedidos=("pedidos", "sum"), exp=("pedidos_expedidos_cutoff", "sum"))
        .reset_index()
    )
    for rid in cfg.REGIOES:
        c = cut[cut.regiao_id == rid].set_index("data").reindex(cal.data)
        volumes = (c.pedidos.fillna(0) * 1.12).to_numpy()  # pedidos multi-volume
        aderencia_cd = np.where(c.pedidos > 0, c.exp / c.pedidos.replace(0, np.nan), 1).astype(float)
        ativo = volumes > 0
        viagens = np.ceil(volumes / (PACOTES_POR_CARRETA * 0.82)).astype(int)
        ocupacao = np.where(viagens > 0, volumes / np.maximum(viagens * PACOTES_POR_CARRETA, 1), 0)
        janelas = efeito(cal.data, "janelas_linehaul")
        otd_p = np.clip(0.93 * aderencia_cd + 0.06 + 0.025 * janelas + rng.normal(0, 0.012, len(cal)), 0.5, 1)
        pen_dist = {"SE": 0.0, "S": 0.01, "CO": 0.03, "NE": 0.035, "N": 0.07}[rid]
        ota = np.clip(otd_p - pen_dist * (1 - 0.5 * janelas) - 0.02 + rng.normal(0, 0.012, len(cal)), 0.4, 1)
        km = viagens * DISTANCIA_LINEHAUL_KM[rid] * 2
        km_vazio = np.clip(rng.normal(0.24 if rid in ("N", "NE") else 0.18, 0.03, len(cal)), 0.05, 0.5)
        viagens_l.append(
            pd.DataFrame(
                {
                    "data": cal.data,
                    "regiao_id": rid,
                    "viagens": viagens,
                    "partidas_no_horario": np.round(viagens * otd_p).astype(int),
                    "chegadas_na_janela": np.round(viagens * ota).astype(int),
                    "volumes": volumes.round().astype(int),
                    "kg": (volumes * 1.8).round(),
                    "ocupacao_media": ocupacao.round(3),
                    "km_total": km,
                    "km_vazio": (km * km_vazio).round(),
                    "custo_frete": (km * CUSTO_KM_CARRETA * rng.normal(1, 0.04, len(cal))).round(2),
                }
            )
        )
        for _, hub in unidades[(unidades.tipo == "HUB") & (unidades.regiao_id == rid)].iterrows():
            util = volumes / (hub.capacidade_dia * _fator_capacidade(cal, rid) * _reforco_pico(cal, 0.8))
            ce = cfg.CAUSA_ESPECIAL
            pane = (hub.unidade_id == ce["unidade"]) & cal.data.between(
                pd.Timestamp(ce["inicio"]), pd.Timestamp(ce["fim"])
            ).to_numpy()
            dwell = np.clip(
                3.5
                + 10 * np.clip(util - 0.85, 0, None)
                + 2.5 * (hub.modelo == "3PL")
                + rng.gamma(2, 0.5, len(cal))
                + 14 * pane,
                1.5,
                96,
            )
            missort_ppm = np.clip(
                rng.normal(900 if hub.modelo == "3PL" else 550, 90, len(cal))
                + 1500 * np.clip(util - 1, 0, None)
                + 4000 * pane,
                100,
                None,
            )
            backlog = np.round(
                volumes
                * np.clip(
                    0.004 + 0.12 * np.clip(util - 0.95, 0, None) + 0.18 * pane + rng.normal(0, 0.002, len(cal)), 0, 1
                )
            )
            hubs_l.append(
                pd.DataFrame(
                    {
                        "data": cal.data,
                        "unidade_id": hub.unidade_id,
                        "volumes_triados": volumes.round().astype(int) * ativo,
                        "dwell_time_p90_h": np.where(ativo, dwell, np.nan).round(2),
                        "volumes_missort": np.round(volumes * missort_ppm / 1e6).astype(int) * ativo,
                        "backlog_fechamento_onda": backlog.astype(int) * ativo,
                    }
                )
            )
    return pd.concat(viagens_l, ignore_index=True), pd.concat(hubs_l, ignore_index=True)


def _last_mile(cal, linehaul, hubs, unidades, rng):
    linhas = []
    hub_reg = hubs.merge(unidades[["unidade_id", "regiao_id"]], on="unidade_id")
    for rid, reg in cfg.REGIOES.items():
        lh = linehaul[linehaul.regiao_id == rid].set_index("data").reindex(cal.data)
        hb = (
            hub_reg[hub_reg.regiao_id == rid]
            .groupby("data")
            .agg(back=("backlog_fechamento_onda", "sum"), vol=("volumes_triados", "sum"))
            .reindex(cal.data)
        )
        vol = lh.volumes.fillna(0).to_numpy()
        ota = np.where(lh.viagens > 0, lh.chegadas_na_janela / lh.viagens.replace(0, np.nan), 1).astype(float)
        taxa_backlog = np.nan_to_num(hb.back / hb.vol.replace(0, np.nan)).astype(float)
        bases = unidades[(unidades.tipo == "BASE") & (unidades.regiao_id == rid)]
        dias_regiao = _dias_operando(cal.data, pd.Timestamp(reg["entrada"]))
        for _, b in bases.iterrows():
            share = b.capacidade_dia / bases.capacidade_dia.sum()
            pacotes = np.round(vol * share).astype(int)
            ativo = pacotes > 0
            e_3pl = b.modelo == "3PL"
            util = pacotes / (b.capacidade_dia * _fator_capacidade(cal, rid) * _reforco_pico(cal, 0.75))
            roteir = efeito(cal.data, "roteirizacao_eta")
            pudo = efeito(cal.data, "rede_pudo", 120) * (rid in ("SE", "S", "NE"))
            aprend = _curva_aprendizagem(dias_regiao, tau=60)
            sobre = np.clip(util - 0.9, 0, None)
            fadr = np.clip(
                0.925
                - 0.02 * e_3pl
                - (0.05 if rid == "N" else 0.0)
                - 0.25 * sobre
                - 0.05 * (1 - aprend)
                + 0.02 * roteir
                + 0.012 * pudo
                + rng.normal(0, 0.007, len(cal)),
                0.6,
                0.99,
            )
            otd = np.clip(
                0.35 + 0.62 * ota - 1.2 * taxa_backlog - 0.3 * sobre - 0.01 * e_3pl + rng.normal(0, 0.008, len(cal)),
                0.4,
                0.995,
            )
            anos = (cal.data - pd.Timestamp(cfg.INICIO)).dt.days.to_numpy() / 365
            regional = efeito(cal.data, "cds_regionais", 120) * (rid in ("NE", "CO"))
            p48 = np.clip(
                PRAZO_48H_BASE[rid] * (0.6 + 0.4 * otd) / 0.98 * (1 + 0.10 * anos)
                + 0.12 * regional
                + rng.normal(0, 0.01, len(cal)),
                0.05,
                0.95,
            )
            horas_rota = pacotes / (14.5 * (0.85 + 0.15 * aprend)) * (1 + 0.35 * (rid == "N"))
            custo_unit = (
                reg["custo_lm"]
                * (1.07 if e_3pl else 1.0)
                * (1 + 0.5 * (1 - fadr))
                * (1 - 0.07 * pudo)
                * (1 - 0.04 * roteir)
            )
            tentativas_mal = np.round(pacotes * (1 - fadr)).astype(int)
            linhas.append(
                pd.DataFrame(
                    {
                        "data": cal.data,
                        "unidade_id": b.unidade_id,
                        "pacotes_em_rota": pacotes,
                        "entregues_primeira_tentativa": np.round(pacotes * fadr).astype(int),
                        "entregues_total": np.round(pacotes * np.clip(fadr + 0.055, 0, 0.998)).astype(int),
                        "pedidos_promessa_vencida": pacotes,
                        "entregues_no_prazo": np.round(pacotes * otd).astype(int),
                        "entregues_ate_48h": np.round(pacotes * p48).astype(int),
                        "paradas": np.round(pacotes * 0.9).astype(int),
                        "horas_em_rota": horas_rota.round(1),
                        "tentativas_malsucedidas": tentativas_mal,
                        "tentativas_falsas": rng.binomial(tentativas_mal, 0.012 if e_3pl else 0.004),
                        "ocorrencias": rng.binomial(pacotes, 0.0011 if e_3pl else 0.0007),
                        "contatos_sac": rng.binomial(pacotes, np.clip(0.012 - 0.004 * roteir + 0.35 * (1 - otd), 0, 1)),
                        "custo_operacao": (pacotes * custo_unit * rng.normal(1, 0.03, len(cal))).round(2),
                    }
                )[ativo]
            )
    return pd.concat(linhas, ignore_index=True)


# Fatores de risco de saída em 90 dias (log-odds). Premissas de camada D, calibradas para ~33% antes do buddy.
RISCO_SAIDA_90D = {
    "intercepto": -1.15,
    "turno_noite": 0.55,
    "distancia_10km": 0.45,
    "canal_agencia": 0.40,
    "canal_indicacao": -0.55,
    "unidade_3pl": 0.35,
    "admitido_em_pico": 0.30,
    "com_buddy": -0.95,
}


def _colaboradores(m: pd.DataFrame, unidades: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Uma linha por admissão, com atributos de risco e data de desligamento (NaT = ainda ativo)."""
    adm = m.loc[m.index.repeat(m.admissoes), ["mes", "unidade_id", "modelo"]].reset_index(drop=True)
    n = len(adm)
    dias_no_mes = adm.mes.dt.days_in_month.to_numpy()
    adm["data_admissao"] = adm.mes + pd.to_timedelta((rng.random(n) * dias_no_mes).astype(int), unit="D")
    adm["turno"] = rng.choice(["manha", "tarde", "noite"], n, p=[0.40, 0.30, 0.30])
    adm["canal_recrutamento"] = rng.choice(["anuncio", "agencia", "indicacao"], n, p=[0.40, 0.35, 0.25])
    adm["distancia_km"] = np.round(np.clip(rng.lognormal(np.log(9), 0.55, n), 1, 60), 1)
    adm["admitido_em_pico"] = adm.data_admissao.dt.month.isin([10, 11]).to_numpy()
    buddy_disp = efeito(adm.data_admissao, "onboarding_buddy", 120) * np.where(adm.modelo == "3PL", 0.3, 0.9)
    adm["com_buddy"] = rng.random(n) < buddy_disp
    b = RISCO_SAIDA_90D
    logit = (
        b["intercepto"]
        + b["turno_noite"] * (adm.turno == "noite")
        + b["distancia_10km"] * (adm.distancia_km - 9) / 10
        + b["canal_agencia"] * (adm.canal_recrutamento == "agencia")
        + b["canal_indicacao"] * (adm.canal_recrutamento == "indicacao")
        + b["unidade_3pl"] * (adm.modelo == "3PL")
        + b["admitido_em_pico"] * adm.admitido_em_pico
        + b["com_buddy"] * adm.com_buddy
    )
    sai_cedo = rng.random(n) < 1 / (1 + np.exp(-logit.to_numpy()))
    # Saídas precoces concentram-se nas primeiras semanas; depois, risco mensal baixo e constante.
    # Exponencial truncada em 89 dias (inversa da CDF), sem acumular massa no limite.
    escala = 30.0
    dias_cedo = np.ceil(-escala * np.log(1 - rng.random(n) * (1 - np.exp(-89 / escala))))
    dias_tarde = 90 + np.ceil(rng.exponential(900, n))
    dias = np.where(sai_cedo, dias_cedo, dias_tarde)
    saida = adm.data_admissao + pd.to_timedelta(dias, unit="D")
    adm["data_desligamento"] = saida.where(saida <= pd.Timestamp(cfg.FIM))
    adm["motivo"] = np.where(
        adm.data_desligamento.isna(), "", rng.choice(["voluntario", "involuntario"], n, p=[0.7, 0.3])
    )
    adm = adm.merge(unidades[["unidade_id", "regiao_id"]], on="unidade_id")
    adm.insert(0, "colaborador_id", [f"C{i:06d}" for i in range(1, n + 1)])
    return adm.drop(columns="mes")


def _pessoas(cds, unidades, rng):
    base = cds.merge(unidades[["unidade_id", "modelo", "data_inicio"]], on="unidade_id")
    base["mes"] = base.data.dt.to_period("M").dt.to_timestamp()
    m = (
        base.groupby(["mes", "unidade_id", "modelo", "data_inicio"])
        .agg(hh=("horas_homem", "sum"), absent=("absenteismo", "mean"))
        .reset_index()
    )
    m = m[m.hh > 0].copy()
    m["headcount"] = np.round(m.hh / (8 * 25 * (1 - m.absent))).astype(int)
    # Reposição dos veteranos (quadro anterior a 2025) + crescimento do quadro.
    saidas_veteranos = np.round(
        m.headcount * np.where(m.modelo == "3PL", 0.045, 0.025) * rng.normal(1, 0.15, len(m))
    ).astype(int)
    unidade_nova = m.data_inicio > pd.Timestamp(cfg.INICIO)
    crescimento = m.groupby("unidade_id").headcount.diff()
    crescimento = crescimento.fillna(m.headcount.where(unidade_nova, 0)).clip(lower=0)
    m["admissoes"] = np.round(saidas_veteranos + crescimento * 1.15).astype(int)  # +15%: reposição dos novatos

    colab = _colaboradores(m, unidades, rng)
    colab["mes_admissao"] = colab.data_admissao.dt.to_period("M").dt.to_timestamp()
    colab["mes_saida"] = colab.data_desligamento.dt.to_period("M").dt.to_timestamp()
    tempo = (colab.data_desligamento - colab.data_admissao).dt.days
    precoce = colab[tempo < 90].groupby(["mes_admissao", "unidade_id"]).size()
    saidas = colab.dropna(subset=["mes_saida"]).groupby(["mes_saida", "unidade_id"]).size()
    chave = pd.MultiIndex.from_frame(m[["mes", "unidade_id"]])
    m["desligamentos"] = saidas_veteranos + saidas.reindex(chave, fill_value=0).to_numpy()
    m["desligamentos_menos_90d"] = precoce.reindex(chave, fill_value=0).to_numpy()
    # Coorte madura: todos os admitidos do mês já completaram 90 dias no fim dos dados (evita viés de censura).
    m["coorte_madura"] = (m.mes + pd.offsets.MonthEnd(0) + pd.Timedelta(days=90)) <= pd.Timestamp(cfg.FIM)
    m["horas_trabalhadas"] = m.hh.round()
    m["acidentes"] = rng.poisson(m.hh * 9e-6)
    m["dias_perdidos"] = rng.poisson(m.acidentes * 12)
    m["enps"] = np.clip(rng.normal(np.where(m.modelo == "3PL", 5, 18), 8), -100, 100).round()
    pessoas = m.drop(columns=["hh", "absent", "data_inicio"])
    return pessoas, colab.drop(columns=["mes_admissao", "mes_saida"])


def gerar(semente: int = cfg.SEMENTE) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(semente)
    cal = _calendario()
    unidades = _dim_unidade()
    demanda = _demanda(cal, rng)
    midia = _midia(cal, demanda, rng)
    cds = _cds(cal, demanda, unidades, rng)
    linehaul, hubs = _linehaul_hubs(cal, cds, unidades, rng)
    lm = _last_mile(cal, linehaul, hubs, unidades, rng)
    pessoas, colaboradores = _pessoas(cds, unidades, rng)
    return {
        "dim_calendario": cal,
        "dim_regiao": _dim_regiao(),
        "dim_unidade": unidades,
        "fato_demanda": demanda,
        "fato_midia": midia,
        "fato_cd": cds,
        "fato_linehaul": linehaul,
        "fato_hub": hubs,
        "fato_last_mile": lm,
        "fato_pessoas": pessoas,
        "fato_colaboradores": colaboradores,
        "fato_recebimentos_am1": gerar_recebimentos(),
    }


def salvar(dados: dict[str, pd.DataFrame], pasta: Path = PASTA_DADOS) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    for nome, df in dados.items():
        df.to_csv(pasta / f"{nome}.csv", index=False)


def carregar(pasta: Path = PASTA_DADOS) -> dict[str, pd.DataFrame]:
    """Lê os CSVs gerados; se não existirem, gera em memória."""
    if not (pasta / "fato_cd.csv").exists():
        return gerar()
    dados = {}
    for arq in sorted(pasta.glob("*.csv")):
        df = pd.read_csv(arq)
        for col in ("data", "mes", "data_inicio", "data_entrada", "data_admissao", "data_desligamento", "chegada"):
            if col in df:
                df[col] = pd.to_datetime(df[col])
        dados[arq.stem] = df
    return dados


if __name__ == "__main__":
    d = gerar()
    salvar(d)
    for nome, df in d.items():
        print(f"{nome:<16}{len(df):>8} linhas")
