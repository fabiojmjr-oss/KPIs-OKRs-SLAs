import csv
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from kpikit import capacidade, kpis, okr, simulador, spc

RAIZ = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def dados():
    return simulador.gerar()


def test_simulador_reprodutivel(dados):
    outra = simulador.gerar()
    pd.testing.assert_frame_equal(dados["fato_cd"], outra["fato_cd"])


def test_registro_existe_no_catalogo():
    with (RAIZ / "catalogo" / "kpis.csv").open(encoding="utf-8") as f:
        ids = {l["id"] for l in csv.DictReader(f, delimiter=";")}
    assert set(kpis.REGISTRO) <= ids


def test_razao_agregada_por_soma_nao_por_media():
    d = {"fato_cd": pd.DataFrame({
            "data": pd.to_datetime(["2025-01-01", "2025-01-02"]), "unidade_id": ["X", "X"],
            "pedidos": [100, 10_000], "pedidos_expedidos_cutoff": [50, 9_900]}),
         "dim_unidade": pd.DataFrame({"unidade_id": ["X"], "regiao_id": ["SE"], "modelo": ["proprio"],
                                      "tipo": ["CD"]})}
    assert kpis.calcular(d, "SC-009") == pytest.approx(9_950 / 10_100)


@pytest.mark.parametrize("kpi_id", list(kpis.REGISTRO))
def test_todos_kpis_calculam(dados, kpi_id):
    v = kpis.calcular(dados, kpi_id)
    assert np.isfinite(v)


def test_carta_p_laney_reduz_falsos_alarmes(dados):
    cd = dados["fato_cd"].query("unidade_id == 'CD-SP1'").set_index("data")
    nc = cd.pedidos - cd.pedidos_expedidos_cutoff
    classica = spc.regras_nelson(spc.carta_p(nc, cd.pedidos, laney=False)).regra_1.sum()
    laney = spc.regras_nelson(spc.carta_p(nc, cd.pedidos)).regra_1.sum()
    assert laney < classica


def test_imr_detecta_causa_especial_injetada(dados):
    hub = dados["fato_hub"].query("unidade_id == 'HUB-BA'").set_index("data").dwell_time_p90_h.dropna()
    sinais = spc.regras_nelson(spc.carta_imr(hub)).regra_1
    assert sinais.loc["2025-09-16":"2025-09-18"].all()


def test_capabilidade_normal_conhecida():
    x = pd.Series(np.random.default_rng(0).normal(10, 1, 5_000))
    r = spc.capabilidade(x, lie=7, lse=13)
    assert r["Ppk"] == pytest.approx(1.0, abs=0.05)


def test_nivel_sigma_convencao():
    assert spc.nivel_sigma(3.4) == pytest.approx(6.0, abs=0.01)


def test_nota_kr_polaridades():
    assert okr.nota_kr(0.90, 0.96, 0.93) == pytest.approx(0.5)
    assert okr.nota_kr(14.0, 12.0, 13.0) == pytest.approx(0.5)   # menor é melhor
    assert okr.nota_kr(0.90, 0.96, 0.85) == 0.0
    assert okr.nota_kr(0.90, 0.96, 0.99) == 1.0


def test_okrs_pontuam(dados):
    krs, objs = okr.pontuar(dados)
    assert len(objs) == 4 and krs.nota.between(0, 1).all()


def test_otimizador_respeita_restricoes(dados):
    dem = capacidade.demanda_projetada(dados)
    cen = capacidade.Cenario(demanda=dem)
    r = capacidade.otimizar(cen)
    assert r.status == "otimo"
    p = r.plano
    ped = p[["ped_proprio", "ped_extra", "ped_temporario", "pedidos_3pl"]].sum(axis=1)
    assert (ped >= p.demanda * (1 + cen.buffer_sla) - 1).all()
    assert (p.acuracia_mix >= cen.acuracia_meta - 1e-6).all()
    assert (p.pedidos_3pl <= cen.limite_3pl * p.demanda + 1).all()
    assert (p.contratacoes <= cen.max_contratacoes_semana + 1e-6).all()


def test_meta_de_acuracia_mais_alta_nunca_custa_menos(dados):
    dem = capacidade.demanda_projetada(dados)
    curva = capacidade.curva_tradeoff(capacidade.Cenario(demanda=dem), "acuracia_meta", [0.996, 0.9968, 0.997])
    assert curva.custo_total.is_monotonic_increasing


# ---------------------------------------------------------------- pessoas
from kpikit import config as cfg, dmaic, pessoas  # noqa: E402


def test_kaplan_meier_sem_censura_e_proporcao_simples():
    dias = pd.Series([10, 20, 30, 40])
    km = pessoas.kaplan_meier(dias, pd.Series([1, 1, 1, 1]))
    assert pessoas.sobrevivencia_em(km, 25) == pytest.approx(0.5)


def test_kaplan_meier_trata_censura():
    # 2 saem no dia 10; 2 ainda ativos (censurados) no dia 5 → quem restou em risco no dia 10 são 2
    km = pessoas.kaplan_meier(pd.Series([5, 5, 10, 10]), pd.Series([0, 0, 1, 1]))
    assert pessoas.sobrevivencia_em(km, 10) == pytest.approx(0.0)


def test_logistica_recupera_efeito_do_buddy(dados):
    X, y = pessoas.matriz_risco_saida(dados["fato_colaboradores"], cfg.FIM)
    m = pessoas.regressao_logistica(X, y)
    assert m.loc["com_buddy", "razao_chances"] < 0.6 and m.loc["com_buddy", "p_valor"] < 0.001


def test_pe003_usa_apenas_coortes_maduras(dados):
    import math
    assert math.isnan(kpis.calcular(dados, "PE-003", inicio="2026-08-01", fim="2026-09-30"))


def test_previsao_absenteismo_bate_regua_ingenua(dados):
    _, m = pessoas.previsao_absenteismo(dados)
    assert m["mae_modelo_pp"] < m["mae_ingenuo_pp"]


def test_escala_cobre_necessidade_e_economiza():
    nec = pd.Series([100, 90, 90, 90, 80, 60, 50], index=pessoas.DIAS)
    ab = pd.Series([0.06] + [0.05] * 6, index=pessoas.DIAS)
    r = pessoas.escala_6x1(nec, ab)
    assert (r.cobertura.presentes_esperados >= nec.to_numpy() - 1e-6).all()
    assert r.quadro <= r.quadro_ingenuo
    assert pessoas.escala_6x1(nec, ab, folga_domingo_min=0.5).quadro >= r.quadro


# ---------------------------------------------------------------- dmaic
@pytest.fixture(scope="module")
def recebimentos():
    return dmaic.gerar_recebimentos()


def test_dmaic_causas_plantadas_sao_detectadas(recebimentos):
    base = recebimentos[recebimentos.fase == "medir"]
    assert dmaic.comparar_grupos(base, "agendado")["mann_whitney_p"] < 0.001
    assert dmaic.qui_quadrado(base, "fornecedor")["p_valor"] < 0.001


def test_dmaic_media_e_cauda_tem_causas_diferentes(recebimentos):
    base = recebimentos[recebimentos.fase == "medir"]
    assert dmaic.pareto(base).index[0] == "espera_doca_h"
    assert dmaic.pareto(base, so_cauda=True).index[0] == "tratativa_divergencia_h"


def test_dmaic_piloto_melhora_capability(recebimentos):
    antes = dmaic.capabilidade_nao_normal(recebimentos.query("fase == 'medir'").dock_to_stock_h)
    depois = dmaic.capabilidade_nao_normal(recebimentos.query("fase == 'piloto'").dock_to_stock_h)
    assert antes["ppk_percentil"] < 1.0 <= depois["ppk_percentil"]
    assert antes["ppk_normal_enganoso"] > antes["ppk_percentil"]   # normal superestima em cauda longa


# ---------------------------------------------------------------- middle mile
from kpikit import middle_mile as mm  # noqa: E402


def test_consolidacao_respeita_capacidade_e_limite_inferior():
    lotes = mm.gerar_lotes(80)
    v = mm.FROTA["Truck"]
    r = mm.resumo_ocupacao(mm.consolidar(lotes, v), v)
    assert (r.ocup_peso <= 1 + 1e-9).all() and (r.ocup_volume <= 1 + 1e-9).all()
    assert len(r) >= mm.limite_inferior_veiculos(lotes, v)


def test_ecommerce_enche_por_volume():
    v = mm.FROTA["Truck"]
    r = mm.resumo_ocupacao(mm.consolidar(mm.gerar_lotes(80), v), v)
    assert (r.restricao_ativa == "volume").mean() > 0.5


def test_otimo_nunca_pior_que_heuristica():
    lotes = mm.gerar_lotes(25, semente=5)
    v = mm.FROTA["VUC"]
    n_otimo, _ = mm.consolidar_otimo(lotes, v)
    assert mm.limite_inferior_veiculos(lotes, v) <= n_otimo <= mm.consolidar(lotes, v).veiculo.nunique()


def test_mix_frota_cobre_carga():
    mix = mm.mix_frota(30_000, 170, 240)
    frota = {v.nome: v for v in mm.FROTA.values()}
    assert sum(frota[n].peso_kg * q for n, q in zip(mix.veiculo, mix.quantidade)) >= 30_000
    assert sum(frota[n].volume_m3 * q for n, q in zip(mix.veiculo, mix.quantidade)) >= 170


def test_esperar_encher_sem_trava_perde_prazo():
    v = mm.FROTA["Carreta"]
    com = mm.simular_despacho(350, v, 240, "encher", 1.0)
    sem = mm.simular_despacho(350, v, 240, "encher", 1.0, trava_h=np.inf)
    assert sem.ocupacao_media > com.ocupacao_media and sem.pct_volume_no_prazo < com.pct_volume_no_prazo


def test_clarke_wright_viavel_e_melhor_que_direto():
    C = mm.CIDADES_NE
    D = mm.matriz_distancias(C)
    kg = C.demanda_kg.to_numpy(float)
    m3 = kg / mm.DENSIDADE_ECOMMERCE_KG_M3
    v = mm.FROTA["Truck"]
    rotas = mm.clarke_wright(kg, m3, D, v, km_max=900)
    atendidas = sorted(c for r in rotas for c in r)
    assert set(atendidas) == set(range(1, len(C)))
    ev = mm.avaliar_rotas(rotas, kg, m3, D, v)
    assert (ev.kg <= v.peso_kg + 1e-6).all() and (ev.m3 <= v.volume_m3 + 1e-6).all()
    assert ev.km.sum() < mm.avaliar_rotas(mm.rotas_diretas(kg, m3, v), kg, m3, D, v).km.sum()


def test_dois_opt_desfaz_cruzamento():
    pts = pd.DataFrame({"lat": [0, 0, 1, 1, 0], "lon": [0, 1, 1, 0, 2]})   # hub + 4 pontos
    D = mm.matriz_distancias(pts)
    cruzada = [1, 3, 2, 4]
    assert mm.comprimento(mm.dois_opt(cruzada, D), D) < mm.comprimento(cruzada, D)


def test_rede_sem_transbordo_igual_ao_milk_run_da_secao_3():
    r = mm.avaliar_rede([])
    ref = mm.comparar_cenarios(km_max=900).loc["milk run + right-sizing", "custo"]
    assert r["custo_dia"] == pytest.approx(ref)


def test_rede_atende_todas_as_cidades():
    r = mm.avaliar_rede(["Patos", "Caruaru"])
    assert r["chegada_h"].notna().all()
    assert len(r["chegada_h"]) == len(mm.CIDADES_NE) - 1


def test_onda_antecipada_nunca_piora_o_prazo():
    base = mm.avaliar_rede(["Patos"])
    antecipada = mm.avaliar_rede(["Patos"], p=mm.ParametrosRede(antecipacao_linehaul_h=3))
    assert antecipada["pct_demanda_no_prazo"] >= base["pct_demanda_no_prazo"]
    assert antecipada["custo_dia"] == pytest.approx(base["custo_dia"])


def test_orientar_nao_muda_km():
    D = mm.matriz_distancias(mm.CIDADES_NE)
    kg = mm.CIDADES_NE.demanda_kg.to_numpy(float)
    rota = [1, 2, 13, 12]
    assert mm.comprimento(mm._orientar(rota, D, kg, mm.ParametrosRede()), D) == pytest.approx(mm.comprimento(rota, D))
