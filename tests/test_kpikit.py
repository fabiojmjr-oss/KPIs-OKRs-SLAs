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
