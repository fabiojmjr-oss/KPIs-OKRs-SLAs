"""Middle mile: consolidação de carga, política de despacho e roteirização milk run.

Três decisões que determinam custo e pontualidade entre o CD/hub e as bases:
1. Como encher o veículo?               → consolidar (heurística FFD) · consolidar_otimo (MILP) · mix_frota
2. Esperar encher ou sair no horário?   → simular_despacho · curva_despacho
3. Qual a sequência de paradas?         → clarke_wright + dois_opt · rotas_diretas

Especificações de veículos, custos e coordenadas são premissas de camada D (aproximadas).
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field, replace

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp


@dataclass(frozen=True)
class Veiculo:
    nome: str
    peso_kg: float
    volume_m3: float
    custo_km: float
    custo_fixo_dia: float


# ⚠️ Premissas típicas de mercado; variam por implemento, carroceria e contrato.
FROTA = {
    "VUC": Veiculo("VUC", 3_000, 18, 3.2, 350),
    "Toco": Veiculo("Toco", 6_000, 35, 4.5, 450),
    "Truck": Veiculo("Truck", 12_000, 50, 5.8, 550),
    "Carreta": Veiculo("Carreta", 25_000, 90, 7.8, 750),
}
FATOR_CUBAGEM_KG_M3 = 300  # ⚠️ prática comum no rodoviário brasileiro para peso cubado
FATOR_SINUOSIDADE = 1.25  # distância rodoviária ≈ 1,25 × distância em linha reta (premissa)
# ⚠️ Jornada: rota acima de ~11 h (8 h + 2 h extras + paradas) exige pernoite ou segundo motorista
# (Lei 13.103/2015 e convenção coletiva — validar com o jurídico). Custo é premissa D.
JORNADA_MAX_H = 11.0
CUSTO_PERNOITE = 450.0


# ---------------------------------------------------------------- 1. Consolidação
def gerar_lotes(n: int, densidade_kg_m3: float = 150, semente: int = 3) -> pd.DataFrame:
    """Lotes (pallets/gaiolas) de e-commerce: leves e volumosos (densidade ~150 kg/m³)."""
    rng = np.random.default_rng(semente)
    vol = np.round(rng.uniform(0.6, 2.2, n), 2)
    dens = rng.normal(densidade_kg_m3, densidade_kg_m3 * 0.35, n).clip(40, 600)
    return pd.DataFrame(
        {"lote": [f"L{i:03d}" for i in range(1, n + 1)], "volume_m3": vol, "peso_kg": np.round(vol * dens)}
    )


def consolidar(lotes: pd.DataFrame, veiculo: Veiculo) -> pd.DataFrame:
    """First-Fit Decreasing em 2 dimensões (peso e m³). Ordena pela dimensão dominante de cada lote."""
    dominante = np.maximum(lotes.peso_kg / veiculo.peso_kg, lotes.volume_m3 / veiculo.volume_m3)
    ordem = lotes.assign(_dom=dominante).sort_values("_dom", ascending=False)
    cargas: list[list[float]] = []  # [peso, volume] por veículo
    alocacao = {}
    for _, lt in ordem.iterrows():
        for i, (p, v) in enumerate(cargas):
            if p + lt.peso_kg <= veiculo.peso_kg and v + lt.volume_m3 <= veiculo.volume_m3:
                cargas[i] = [p + lt.peso_kg, v + lt.volume_m3]
                alocacao[lt.lote] = i
                break
        else:
            cargas.append([lt.peso_kg, lt.volume_m3])
            alocacao[lt.lote] = len(cargas) - 1
    return lotes.assign(veiculo=lotes.lote.map(alocacao))


def resumo_ocupacao(alocado: pd.DataFrame, veiculo: Veiculo) -> pd.DataFrame:
    """Ocupação por veículo em peso e em m³. A 'restrição ativa' é a que está mais cheia (MM-003)."""
    r = alocado.groupby("veiculo").agg(
        peso_kg=("peso_kg", "sum"), volume_m3=("volume_m3", "sum"), lotes=("lote", "size")
    )
    r["ocup_peso"] = r.peso_kg / veiculo.peso_kg
    r["ocup_volume"] = r.volume_m3 / veiculo.volume_m3
    r["restricao_ativa"] = np.where(r.ocup_volume >= r.ocup_peso, "volume", "peso")
    r["ocupacao"] = r[["ocup_peso", "ocup_volume"]].max(axis=1)
    return r


def limite_inferior_veiculos(lotes: pd.DataFrame, veiculo: Veiculo) -> int:
    """Nenhuma solução usa menos veículos que isso (soma de peso ou volume ÷ capacidade)."""
    return int(np.ceil(max(lotes.peso_kg.sum() / veiculo.peso_kg, lotes.volume_m3.sum() / veiculo.volume_m3)))


def consolidar_otimo(
    lotes: pd.DataFrame, veiculo: Veiculo, max_veiculos: int | None = None, tempo_limite: float = 20.0
) -> tuple[int, pd.DataFrame]:
    """Bin packing 2D exato por programação inteira (use em instâncias pequenas, até ~40 lotes).

    Variáveis: x[i,b] = lote i no veículo b; y[b] = veículo b usado. Minimiza Σ y.
    """
    n = len(lotes)
    B = max_veiculos or len(consolidar(lotes, veiculo).veiculo.unique())
    nx = n * B
    c = np.concatenate([np.zeros(nx), np.ones(B)])
    linhas, lb, ub = [], [], []
    for i in range(n):  # cada lote em exatamente um veículo
        r = np.zeros(nx + B)
        r[i * B : (i + 1) * B] = 1
        linhas.append(r)
        lb.append(1)
        ub.append(1)
    for b in range(B):  # capacidade em peso e em volume
        for col, cap in (("peso_kg", veiculo.peso_kg), ("volume_m3", veiculo.volume_m3)):
            r = np.zeros(nx + B)
            r[[i * B + b for i in range(n)]] = lotes[col].to_numpy()
            r[nx + b] = -cap
            linhas.append(r)
            lb.append(-np.inf)
            ub.append(0)
    for b in range(B - 1):  # quebra de simetria: usa veículos em ordem
        r = np.zeros(nx + B)
        r[nx + b] = 1
        r[nx + b + 1] = -1
        linhas.append(r)
        lb.append(0)
        ub.append(np.inf)
    res = milp(
        c,
        constraints=LinearConstraint(np.array(linhas), lb, ub),
        integrality=np.ones(nx + B),
        bounds=Bounds(0, 1),
        options={"time_limit": tempo_limite},
    )
    if res.x is None:
        raise ValueError(f"Sem solução: {res.message}")
    x = np.round(res.x[:nx]).reshape(n, B)
    return round(res.x[nx:].sum()), lotes.assign(veiculo=x.argmax(axis=1))


def mix_frota(peso_kg: float, volume_m3: float, km_ida_volta: float, frota: dict = FROTA) -> pd.DataFrame:
    """Combinação de veículos de menor custo para levar peso e volume numa rota (programação inteira)."""
    vs = list(frota.values())
    custo = np.array([v.custo_fixo_dia + v.custo_km * km_ida_volta for v in vs])
    A = np.array([[v.peso_kg for v in vs], [v.volume_m3 for v in vs]])
    res = milp(
        custo,
        constraints=LinearConstraint(A, lb=[peso_kg, volume_m3], ub=np.inf),
        integrality=np.ones(len(vs)),
        bounds=Bounds(0, np.inf),
    )
    qtd = np.round(res.x).astype(int)
    out = pd.DataFrame({"veiculo": [v.nome for v in vs], "quantidade": qtd, "custo": qtd * custo})
    return out[out.quantidade > 0].reset_index(drop=True)


# ---------------------------------------------------------------- 2. Política de despacho
PERFIL_CHEGADA_HUB = np.array(
    [
        0.5,
        0.4,
        0.3,
        0.3,
        0.4,
        0.8,
        1.2,
        1.6,
        1.9,
        2.0,
        1.9,
        1.7,
        1.5,
        1.4,
        1.5,
        1.7,
        2.0,
        2.3,
        2.4,
        2.2,
        1.8,
        1.3,
        0.9,
        0.6,
    ]
)


@dataclass
class ResultadoDespacho:
    politica: str
    parametro: float
    viagens_dia: float
    ocupacao_media: float
    custo_por_m3: float
    pct_volume_no_prazo: float
    espera_media_h: float
    detalhe: pd.DataFrame = field(repr=False, default=None)


def simular_despacho(
    volume_dia_m3: float,
    veiculo: Veiculo,
    km_ida_volta: float,
    politica: str,
    parametro: float,
    prazo_h: float = 8.0,
    dias: int = 60,
    semente: int = 11,
    trava_h: float | None = None,
) -> ResultadoDespacho:
    """Simula o hub durante `dias` dias, hora a hora.

    politica = "horario":  sai a cada `parametro` horas com o que houver (mín. 5% da capacidade).
    politica = "encher":   sai quando atinge `parametro` (fração da capacidade em m³) ou quando o volume
                           mais antigo esperou `trava_h` horas (trava de serviço; padrão prazo_h/2,
                           use np.inf para "esperar encher" sem trava).
    Um volume está "no prazo" se sai do hub até `prazo_h` horas após chegar.
    """
    trava_h = prazo_h / 2 if trava_h is None else trava_h
    rng = np.random.default_rng(semente)
    perfil = PERFIL_CHEGADA_HUB / PERFIL_CHEGADA_HUB.sum()
    fila: list[list[float]] = []  # [hora_chegada, m3]
    saidas = []
    ultimo = 0.0
    for h in range(dias * 24):
        m3 = rng.poisson(volume_dia_m3 * perfil[h % 24] * 10) / 10
        if m3 > 0:
            fila.append([h, m3])
        while fila:
            total = sum(q for _, q in fila)
            espera_mais_antigo = h - fila[0][0]
            if politica == "horario":
                # Sai no horário; se ainda sobrar carga para um veículo cheio, despacha outro na mesma hora.
                no_horario = (h - ultimo) >= parametro or (h == ultimo and total >= veiculo.volume_m3)
                sair = no_horario and total >= 0.05 * veiculo.volume_m3
            else:
                sair = total >= parametro * veiculo.volume_m3 or espera_mais_antigo >= trava_h
            if not sair:
                break
            carga, cap, restante = [], veiculo.volume_m3, []
            for t0, q in fila:  # FIFO: os mais antigos embarcam primeiro
                embarca = min(q, cap)
                if embarca > 0:
                    carga.append((t0, embarca))
                    cap -= embarca
                if q - embarca > 1e-9:
                    restante.append([t0, q - embarca])
            fila = restante
            ultimo = h
            m3_v = sum(q for _, q in carga)
            saidas.append(
                {
                    "hora": h,
                    "m3": m3_v,
                    "ocupacao": m3_v / veiculo.volume_m3,
                    "m3_no_prazo": sum(q for t0, q in carga if h - t0 <= prazo_h),
                    "espera_ponderada": sum(q * (h - t0) for t0, q in carga),
                }
            )
    s = pd.DataFrame(saidas)
    # Cada viagem ida e volta ocupa meio dia de veículo (premissa: 2 viagens por veículo por dia).
    custo = len(s) * (veiculo.custo_km * km_ida_volta + veiculo.custo_fixo_dia / 2)
    rotulo = politica if politica == "horario" or np.isfinite(trava_h) else "encher_sem_trava"
    return ResultadoDespacho(
        rotulo,
        parametro,
        len(s) / dias,
        float(s.ocupacao.mean()),
        float(custo / s.m3.sum()),
        float(s.m3_no_prazo.sum() / s.m3.sum()),
        float(s.espera_ponderada.sum() / s.m3.sum()),
        s,
    )


def curva_despacho(
    volume_dia_m3: float,
    veiculo: Veiculo,
    km_ida_volta: float,
    prazo_h: float = 8.0,
    limiares=(0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
    intervalos=(2, 3, 4, 6, 8),
) -> pd.DataFrame:
    """Fronteira custo × pontualidade das duas famílias de política."""
    linhas = []
    familias = [("encher", limiares, None), ("encher", limiares, np.inf), ("horario", intervalos, None)]
    for pol, valores, trava in familias:
        for v in valores:
            r = simular_despacho(volume_dia_m3, veiculo, km_ida_volta, pol, v, prazo_h, trava_h=trava)
            linhas.append(
                {
                    k: getattr(r, k)
                    for k in (
                        "politica",
                        "parametro",
                        "viagens_dia",
                        "ocupacao_media",
                        "custo_por_m3",
                        "pct_volume_no_prazo",
                        "espera_media_h",
                    )
                }
            )
    return pd.DataFrame(linhas)


# ---------------------------------------------------------------- 3. Roteirização milk run
# Coordenadas aproximadas (sede municipal); demanda diária fictícia em kg. Volume = kg ÷ densidade.
CIDADES_NE = pd.DataFrame(
    [
        ("Recife (hub)", -8.05, -34.88, 0),
        ("Caruaru", -8.28, -35.98, 5200),
        ("Garanhuns", -8.89, -36.49, 2600),
        ("Vitória de Santo Antão", -8.12, -35.29, 1800),
        ("João Pessoa", -7.12, -34.86, 7800),
        ("Campina Grande", -7.23, -35.88, 4700),
        ("Natal", -5.79, -35.21, 8200),
        ("Mossoró", -5.19, -37.34, 2900),
        ("Maceió", -9.67, -35.74, 7200),
        ("Arapiraca", -9.75, -36.66, 2400),
        ("Caicó", -6.46, -37.10, 900),
        ("Patos", -7.02, -37.28, 1300),
        ("Serra Talhada", -7.99, -38.30, 1100),
        ("Arcoverde", -8.42, -37.05, 1000),
        ("Palmares", -8.68, -35.59, 800),
        ("Goiana", -7.56, -35.00, 900),
        ("Santa Cruz do Capibaribe", -7.96, -36.20, 1400),
        ("Surubim", -7.83, -35.75, 700),
        ("Guarabira", -6.85, -35.49, 800),
        ("Sousa", -6.76, -38.23, 900),
        ("Penedo", -10.29, -36.58, 700),
    ],
    columns=["cidade", "lat", "lon", "demanda_kg"],
)
DENSIDADE_ECOMMERCE_KG_M3 = 150


def matriz_distancias(cidades: pd.DataFrame, sinuosidade: float = FATOR_SINUOSIDADE) -> np.ndarray:
    """Distância rodoviária aproximada (km): haversine × fator de sinuosidade."""
    lat, lon = np.radians(cidades.lat.to_numpy()), np.radians(cidades.lon.to_numpy())
    dlat = lat[:, None] - lat[None, :]
    dlon = lon[:, None] - lon[None, :]
    a = np.sin(dlat / 2) ** 2 + np.cos(lat[:, None]) * np.cos(lat[None, :]) * np.sin(dlon / 2) ** 2
    return 2 * 6371 * np.arcsin(np.sqrt(a)) * sinuosidade


def comprimento(rota: list[int], D: np.ndarray) -> float:
    """Distância de hub → paradas → hub (o hub é o índice 0)."""
    caminho = [0, *rota, 0]
    return float(sum(D[a, b] for a, b in itertools.pairwise(caminho)))


def _cabe(kg: float, m3: float, v: Veiculo) -> bool:
    return kg <= v.peso_kg + 1e-9 and m3 <= v.volume_m3 + 1e-9


def rotas_diretas(kg: np.ndarray, m3: np.ndarray, veiculo: Veiculo) -> list[list[int]]:
    """Régua: cada cidade recebe seu(s) próprio(s) veículo(s), ida e volta."""
    rotas = []
    for i in range(1, len(kg)):
        rotas += [[i]] * int(np.ceil(max(kg[i] / veiculo.peso_kg, m3[i] / veiculo.volume_m3)))
    return rotas


def clarke_wright(
    kg: np.ndarray, m3: np.ndarray, D: np.ndarray, veiculo: Veiculo, km_max: float = np.inf
) -> list[list[int]]:
    """Heurística das economias (Clarke & Wright, 1964).

    Parte de uma rota por cliente e une as rotas cujas pontas geram a maior economia
    s(i,j) = d(0,i) + d(0,j) − d(i,j), respeitando peso, volume e extensão máxima da rota.
    Clientes que não cabem sozinhos num veículo ficam em rotas diretas.
    """
    n = len(kg)
    grandes = [i for i in range(1, n) if not _cabe(kg[i], m3[i], veiculo)]
    rotas = {i: [i] for i in range(1, n) if i not in grandes}
    dono = {i: i for i in rotas}
    carga = {i: [kg[i], m3[i]] for i in rotas}
    economias = sorted(((D[0, i] + D[0, j] - D[i, j], i, j) for i in rotas for j in rotas if i < j), reverse=True)
    for s_ij, i, j in economias:
        if s_ij <= 0:
            break
        ri, rj = dono[i], dono[j]
        if ri == rj or not _cabe(carga[ri][0] + carga[rj][0], carga[ri][1] + carga[rj][1], veiculo):
            continue
        a, b = rotas[ri], rotas[rj]
        # i e j precisam ser pontas de suas rotas; orienta para unir ...i + j...
        if a[-1] != i:
            if a[0] != i:
                continue
            a = a[::-1]
        if b[0] != j:
            if b[-1] != j:
                continue
            b = b[::-1]
        nova = a + b
        if comprimento(nova, D) > km_max:
            continue
        rotas[ri] = nova
        carga[ri] = [carga[ri][0] + carga[rj][0], carga[ri][1] + carga[rj][1]]
        for c in b:
            dono[c] = ri
        del rotas[rj], carga[rj]
    return list(rotas.values()) + rotas_diretas(
        np.where(np.isin(np.arange(n), grandes), kg, 0), np.where(np.isin(np.arange(n), grandes), m3, 0), veiculo
    )


def dois_opt(rota: list[int], D: np.ndarray) -> list[int]:
    """Melhoria local: inverte trechos da rota enquanto isso encurtar o percurso (desfaz cruzamentos)."""
    melhor = rota[:]
    melhorou = True
    while melhorou:
        melhorou = False
        for i in range(len(melhor) - 1):
            for k in range(i + 1, len(melhor)):
                candidata = melhor[:i] + melhor[i : k + 1][::-1] + melhor[k + 1 :]
                if comprimento(candidata, D) < comprimento(melhor, D) - 1e-9:
                    melhor, melhorou = candidata, True
    return melhor


def chegadas(rota: list[int], D: np.ndarray, velocidade_kmh: float = 55, parada_h: float = 0.67) -> list[float]:
    """Hora de chegada (desde a saída da origem) em cada parada da rota, na ordem visitada."""
    t, anterior, out = 0.0, 0, []
    for c in rota:
        t += D[anterior, c] / velocidade_kmh
        out.append(t)
        t += parada_h
        anterior = c
    return out


def avaliar_rotas(
    rotas: list[list[int]],
    kg: np.ndarray,
    m3: np.ndarray,
    D: np.ndarray,
    veiculo: Veiculo,
    nomes: list[str] | None = None,
    frota: dict | None = None,
    velocidade_kmh: float = 55,
    parada_h: float = 0.67,
) -> pd.DataFrame:
    """Km, carga, ocupação, horas e custo por rota (inclui pernoite quando a rota excede a jornada).

    frota: se informada, cada rota usa o veículo mais barato que comporta sua carga (right-sizing).
    """
    viagens_por_cidade = pd.Series([r[0] for r in rotas if len(r) == 1]).value_counts()
    linhas = []
    for k, r in enumerate(rotas, 1):
        km = comprimento(r, D)
        div = viagens_por_cidade[r[0]] if len(r) == 1 else 1  # rotas diretas repetidas dividem a carga
        carga_kg, carga_m3 = kg[r].sum() / div, m3[r].sum() / div
        v = veiculo
        if frota:
            cabem = [f for f in frota.values() if _cabe(carga_kg, carga_m3, f)]
            v = min(cabem, key=lambda f: f.custo_fixo_dia + f.custo_km * km) if cabem else veiculo
        horas = km / velocidade_kmh + parada_h * len(r)
        pernoites = int(np.ceil(horas / JORNADA_MAX_H)) - 1
        linhas.append(
            {
                "rota": k,
                "veiculo": v.nome,
                "paradas": len(r),
                "sequencia": " → ".join(nomes[i] for i in r) if nomes else str(r),
                "km": km,
                "kg": carga_kg,
                "m3": carga_m3,
                "ocupacao": max(carga_kg / v.peso_kg, carga_m3 / v.volume_m3),
                "horas": horas,
                "horas_ate_ultima": chegadas(r, D, velocidade_kmh, parada_h)[-1],
                "pernoites": pernoites,
                "custo": v.custo_fixo_dia * (1 + pernoites) + v.custo_km * km + CUSTO_PERNOITE * pernoites,
            }
        )
    return pd.DataFrame(linhas)


def comparar_cenarios(
    cidades: pd.DataFrame = CIDADES_NE,
    veiculo: Veiculo = FROTA["Truck"],
    km_max: float = 1_100,
    densidade: float = DENSIDADE_ECOMMERCE_KG_M3,
) -> pd.DataFrame:
    """Direto × milk run (Clarke-Wright + 2-opt) × milk run com veículo dimensionado por rota."""
    D = matriz_distancias(cidades)
    kg = cidades.demanda_kg.to_numpy(dtype=float)
    m3 = kg / densidade
    nomes = cidades.cidade.tolist()
    diretas = rotas_diretas(kg, m3, veiculo)
    milk = [dois_opt(r, D) for r in clarke_wright(kg, m3, D, veiculo, km_max)]
    cenarios = {
        "direto": avaliar_rotas(diretas, kg, m3, D, veiculo, nomes),
        "milk run": avaliar_rotas(milk, kg, m3, D, veiculo, nomes),
        "milk run + right-sizing": avaliar_rotas(milk, kg, m3, D, veiculo, nomes, frota=FROTA),
    }
    return pd.DataFrame(
        {
            k: {
                "rotas": len(v),
                "km": v.km.sum(),
                "custo": v.custo.sum(),
                "ocupacao_media": v.ocupacao.mean(),
                "maior_rota_h": v.horas.max(),
                "pernoites": v.pernoites.sum(),
                "custo_por_kg": v.custo.sum() / kg.sum(),
            }
            for k, v in cenarios.items()
        }
    ).T


# ---------------------------------------------------------------- 4. Rede com transbordo (hub-and-spoke)
@dataclass(frozen=True)
class ParametrosRede:
    """Premissas (camada D) da rede hub → satélites de transbordo → cidades."""

    custo_fixo_satelite_dia: float = 2_500.0  # aluguel, equipe mínima, equipamentos
    custo_transbordo_m3: float = 6.0  # manuseio do cross-dock
    tempo_transbordo_h: float = 2.0  # descarga, triagem e carregamento
    janela_entrega_h: float = 14.0  # saída do hub (ex.: 22 h) → entrega até 12 h do dia seguinte
    antecipacao_linehaul_h: float = 0.0  # "onda antecipada": carreta do satélite sai X h antes da onda geral
    km_max_hub: float = 900.0
    km_max_satelite: float = 600.0
    velocidade_kmh: float = 55.0
    parada_h: float = 0.67


CANDIDATOS_TRANSBORDO = ["Campina Grande", "Caruaru", "Arcoverde", "Patos"]


def _orientar(rota: list[int], D: np.ndarray, kg: np.ndarray, p: ParametrosRede) -> list[int]:
    """O sentido da rota não muda o km, mas muda quem recebe primeiro: escolhe o sentido que
    entrega mais kg dentro da janela (desempate: menor tempo médio ponderado de chegada)."""

    def nota(r):
        t = np.array(chegadas(r, D, p.velocidade_kmh, p.parada_h))
        return (-(kg[r] * (t <= p.janela_entrega_h)).sum(), (kg[r] * t).sum())

    return min((rota, rota[::-1]), key=nota)


def _cluster(
    cidades: pd.DataFrame,
    origem: int,
    membros: list[int],
    densidade: float,
    veiculo: Veiculo,
    km_max: float,
    p: ParametrosRede,
) -> tuple[pd.DataFrame, dict[str, float]]:
    """Roteiriza os membros a partir da origem. Retorna rotas avaliadas e a hora de chegada por cidade."""
    sub = cidades.iloc[[origem, *membros]].reset_index(drop=True)
    if origem in membros:  # a cidade-satélite é atendida localmente (distância zero)
        sub = cidades.iloc[[origem, *membros]].reset_index(drop=True)
    D = matriz_distancias(sub)
    kg = sub.demanda_kg.to_numpy(float)
    kg[0] = 0.0
    m3 = kg / densidade
    rotas = [_orientar(dois_opt(r, D), D, kg, p) for r in clarke_wright(kg, m3, D, veiculo, km_max)]
    det = avaliar_rotas(
        rotas,
        kg,
        m3,
        D,
        veiculo,
        sub.cidade.tolist(),
        frota=FROTA,
        velocidade_kmh=p.velocidade_kmh,
        parada_h=p.parada_h,
    )
    chegada = {}
    for r in rotas:
        for c, t in zip(r, chegadas(r, D, p.velocidade_kmh, p.parada_h), strict=True):
            chegada[sub.cidade[c]] = min(t, chegada.get(sub.cidade[c], np.inf))
    return det, chegada


def avaliar_rede(
    satelites: list[str],
    cidades: pd.DataFrame = CIDADES_NE,
    p: ParametrosRede | None = None,
    densidade: float = DENSIDADE_ECOMMERCE_KG_M3,
) -> dict:
    """Custo diário e nível de serviço de uma configuração de rede.

    Cada cidade é atendida pela instalação mais próxima (hub ou satélite aberto). Satélites recebem
    carretas do hub (line-haul consolidado) e distribuem com veículos dimensionados por rota.
    """
    p = p or ParametrosRede()
    nomes = cidades.cidade.tolist()
    D = matriz_distancias(cidades)
    inst = [0] + [nomes.index(s) for s in satelites]
    clientes = [i for i in range(1, len(cidades))]
    atrib = {i: min(inst, key=lambda f: D[f, i]) for i in clientes}
    for s in inst[1:]:
        atrib[s] = s  # a própria cidade-satélite é servida pelo satélite
    rotas, linhas_lh, chegada = [], [], {}
    for f in inst:
        membros = [i for i in clientes if atrib[i] == f]
        if not membros:
            continue
        veic = FROTA["Truck"] if f == 0 else FROTA["Toco"]
        km_max = p.km_max_hub if f == 0 else p.km_max_satelite
        membros_rota = [m for m in membros if m != f]
        atraso = 0.0
        if f != 0:
            atraso = D[0, f] / p.velocidade_kmh + p.tempo_transbordo_h - p.antecipacao_linehaul_h
        # No satélite, a janela que sobra para as rotas é a janela total menos o atraso do line-haul.
        p_local = replace(p, janela_entrega_h=p.janela_entrega_h - atraso)
        det, cheg = (
            _cluster(cidades, f, membros_rota, densidade, veic, km_max, p_local)
            if membros_rota
            else (pd.DataFrame(), {})
        )
        if f != 0:
            kg_cl = cidades.demanda_kg.iloc[membros].sum()
            m3_cl = kg_cl / densidade
            carretas = int(np.ceil(max(kg_cl / FROTA["Carreta"].peso_kg, m3_cl / FROTA["Carreta"].volume_m3)))
            km_lh = 2 * D[0, f]
            linhas_lh.append(
                {
                    "satelite": nomes[f],
                    "carretas": carretas,
                    "km": carretas * km_lh,
                    "m3": m3_cl,
                    "ocupacao": m3_cl / (carretas * FROTA["Carreta"].volume_m3),
                    "custo_linehaul": carretas
                    * (FROTA["Carreta"].custo_fixo_dia / 2 + FROTA["Carreta"].custo_km * km_lh),
                    "custo_transbordo": m3_cl * p.custo_transbordo_m3,
                    "custo_fixo": p.custo_fixo_satelite_dia,
                }
            )
            chegada[nomes[f]] = atraso  # entrega local no satélite
        if not det.empty:
            det = det.assign(origem=nomes[f])
            rotas.append(det)
        for c, t in cheg.items():
            chegada[c] = t + atraso
    rotas = pd.concat(rotas, ignore_index=True)
    lh = pd.DataFrame(linhas_lh)
    dem = cidades.set_index("cidade").demanda_kg.drop(nomes[0])
    cheg = pd.Series(chegada).reindex(dem.index)
    no_prazo = float(dem[cheg <= p.janela_entrega_h].sum() / dem.sum())
    custo_rotas = float(rotas.custo.sum())
    custo_lh = float(lh[["custo_linehaul", "custo_transbordo", "custo_fixo"]].sum().sum()) if not lh.empty else 0.0
    return {
        "satelites": " + ".join(satelites) if satelites else "(sem transbordo)",
        "custo_dia": custo_rotas + custo_lh,
        "custo_rotas": custo_rotas,
        "custo_transbordo_total": custo_lh,
        "km": float(rotas.km.sum() + (lh.km.sum() if not lh.empty else 0)),
        "rotas": len(rotas),
        "pernoites": int(rotas.pernoites.sum()),
        "pct_demanda_no_prazo": no_prazo,
        "ultima_entrega_h": float(cheg.max()),
        "cidades_fora_do_prazo": ", ".join(cheg[cheg > p.janela_entrega_h].sort_values(ascending=False).index),
        "detalhe_rotas": rotas,
        "detalhe_linehaul": lh,
        "chegada_h": cheg,
    }


def comparar_redes(
    candidatos: list[str] = CANDIDATOS_TRANSBORDO,
    cidades: pd.DataFrame = CIDADES_NE,
    p: ParametrosRede | None = None,
    max_satelites: int = 2,
) -> pd.DataFrame:
    """Avalia todas as combinações de até `max_satelites` satélites (enumeração completa: poucos candidatos)."""
    p = p or ParametrosRede()
    from itertools import combinations

    linhas = []
    for k in range(max_satelites + 1):
        for combo in combinations(candidatos, k):
            r = avaliar_rede(list(combo), cidades, p)
            linhas.append({c: v for c, v in r.items() if not c.startswith(("detalhe", "chegada"))})
    return pd.DataFrame(linhas).sort_values("custo_dia").reset_index(drop=True)
