"""Parâmetros do caso integrado: Vértice (empresa fictícia).

Premissas de camada D (ver 00-fundamentos/linha-de-base-mercado.md).
Todos os números aqui são de simulação; benchmarks reais estão em BENCHMARKS.
"""

from dataclasses import dataclass, field
from datetime import date

EMPRESA = "Vértice Commerce & Logística (fictícia)"
INICIO = date(2025, 1, 1)
FIM = date(2026, 9, 30)  # "hoje" do caso: fechamento do 3T26
SEMENTE = 42

# Regiões: participação na demanda nacional potencial e data de entrada da operação.
# Sudeste e Sul são a operação madura; as demais entram durante 2025 (expansão nacional).
REGIOES = {
    "SE": {"nome": "Sudeste", "peso": 0.46, "entrada": date(2025, 1, 1), "custo_lm": 11.0},
    "S": {"nome": "Sul", "peso": 0.16, "entrada": date(2025, 1, 1), "custo_lm": 12.0},
    "CO": {"nome": "Centro-Oeste", "peso": 0.09, "entrada": date(2025, 6, 1), "custo_lm": 15.0},
    "NE": {"nome": "Nordeste", "peso": 0.22, "entrada": date(2025, 4, 1), "custo_lm": 14.5},
    "N": {"nome": "Norte", "peso": 0.07, "entrada": date(2025, 8, 1), "custo_lm": 21.0},
}

# Unidades: (id, tipo, região, modelo, capacidade/dia em pedidos ou volumes)
UNIDADES = [
    ("CD-SP1", "CD", "SE", "proprio", 38_000),
    ("CD-SP2", "CD", "SE", "3PL", 20_000),
    ("CD-RJ1", "CD", "SE", "proprio", 16_000),
    ("CD-PR1", "CD", "S", "proprio", 24_000),
    ("CD-GO1", "CD", "CO", "3PL", 13_000),
    ("CD-PE1", "CD", "NE", "proprio", 30_000),
    ("CD-AM1", "CD", "N", "3PL", 9_000),
    ("HUB-SP", "HUB", "SE", "proprio", 90_000),
    ("HUB-PR", "HUB", "S", "proprio", 28_000),
    ("HUB-BA", "HUB", "NE", "3PL", 36_000),
    ("HUB-DF", "HUB", "CO", "3PL", 15_000),
    ("HUB-PA", "HUB", "N", "3PL", 11_000),
    ("LM-SPC", "BASE", "SE", "proprio", 36_000),
    ("LM-SPI", "BASE", "SE", "3PL", 30_000),
    ("LM-RJC", "BASE", "SE", "proprio", 24_000),
    ("LM-CWB", "BASE", "S", "proprio", 15_000),
    ("LM-POA", "BASE", "S", "3PL", 13_000),
    ("LM-GYN", "BASE", "CO", "3PL", 8_000),
    ("LM-BSB", "BASE", "CO", "3PL", 8_000),
    ("LM-REC", "BASE", "NE", "proprio", 14_000),
    ("LM-SSA", "BASE", "NE", "3PL", 12_000),
    ("LM-FOR", "BASE", "NE", "3PL", 10_000),
    ("LM-MAO", "BASE", "N", "3PL", 6_000),
    ("LM-BEL", "BASE", "N", "3PL", 5_500),
]

PEDIDOS_DIA_BASE = 110_000  # demanda média nacional (potencial) fora de pico, jan/2025
CRESCIMENTO_ANUAL = 0.35  # crescimento orgânico a/a
TICKET_MEDIO = 165.0  # R$
MARGEM_CONTRIBUICAO = 0.22  # antes de mídia e logística

# Eventos de sazonalidade: (início, fim, multiplicador de demanda)
EVENTOS = [
    (date(2025, 3, 10), date(2025, 3, 16), 1.35, "Dia do Consumidor"),
    (date(2025, 5, 1), date(2025, 5, 11), 1.30, "Dia das Mães"),
    (date(2025, 11, 24), date(2025, 12, 1), 2.60, "Black Friday / Cyber Monday"),
    (date(2025, 12, 8), date(2025, 12, 20), 1.55, "Natal"),
    (date(2026, 3, 9), date(2026, 3, 15), 1.40, "Dia do Consumidor"),
    (date(2026, 5, 1), date(2026, 5, 10), 1.35, "Dia das Mães"),
]

# Iniciativas 2026 — hipóteses dos OKRs. Cada uma ganha efeito em rampa de ~60 dias a partir do início.
INICIATIVAS = {
    "capacidade_2026": ("Plano de capacidade 2026: novos turnos e expansão de CDs/hubs/bases (+35%)", date(2026, 1, 1)),
    "onboarding_buddy": ("Onboarding padronizado com buddy e trilha de proficiência", date(2026, 1, 15)),
    "wms_scanner": ("Conferência por scanner e endereçamento dirigido no WMS", date(2026, 2, 1)),
    "janelas_linehaul": ("Malha middle mile com janelas sincronizadas (CD → hub → base)", date(2026, 3, 1)),
    "cds_regionais": ("Ampliação dos CDs de NE e CO (estoque mais perto do cliente)", date(2026, 3, 1)),
    "roteirizacao_eta": ("Roteirização dinâmica e ETA proativo ao cliente", date(2026, 4, 1)),
    "midia_poas": ("Alocação de mídia por POAS e testes de incrementalidade", date(2026, 4, 1)),
    "rede_pudo": ("Rede de pontos de retirada (PUDO/lockers) nas capitais", date(2026, 5, 1)),
    "dmaic_am1": ("DMAIC dock-to-stock CD-AM1: agendamento, ASN, recebimento parcial", date(2026, 6, 1)),
}

# Causa especial injetada para demonstração de CEP: pane de sorter no HUB-BA.
CAUSA_ESPECIAL = {"unidade": "HUB-BA", "inicio": date(2025, 9, 16), "fim": date(2025, 9, 18)}

CANAIS_MIDIA = {
    # canal: (participação no orçamento, CPM R$, CTR, conversão, ROAS inflado pela atribuição)
    "Google Search": (0.34, 28.0, 0.045, 0.030, 1.35),
    "Meta Ads": (0.30, 14.0, 0.012, 0.018, 1.55),
    "Google PMax": (0.18, 18.0, 0.020, 0.022, 1.60),
    "TikTok Ads": (0.10, 9.0, 0.009, 0.010, 1.70),
    "Retail Media": (0.08, 22.0, 0.030, 0.035, 1.20),
}
INVESTIMENTO_MIDIA_DIA = 900_000.0  # R$ fora de pico


@dataclass
class Meta:
    """Meta 2026 e benchmark de um KPI estratégico.

    A linha de base NÃO fica aqui: é calculada dos dados (2º semestre de 2025)
    por kpikit.kpis.linha_base(), para nunca divergir da série histórica.
    """

    kpi_id: str
    nome: str
    meta: float
    benchmark: float | None = None
    fonte_benchmark: str = ""
    nivel_confianca: str = "D"
    unidade: str = "%"
    polaridade: str = "maior"


# Metas 2026 do caso — ancoradas nos benchmarks das camadas A/B quando existem.
METAS_2026 = [
    Meta("LM-011", "Pedidos entregues em até 48h", 0.80, 0.77, "Mercado Livre 2T26 — envios rápidos em até 48h", "A"),
    Meta("SC-009", "Expedição no cut-off", 0.99, 0.995, "WERC DC Measures 2025 — best-in-class on-time shipments", "B"),
    Meta("SC-007", "Acurácia de picking", 0.9968, 0.9968, "WERC DC Measures 2025 — best-in-class", "B"),
    Meta("SC-006", "Dock-to-stock P90", 4.0, 3.5, "WERC DC Measures 2025 — best-in-class", "B", "h", "menor"),
    Meta("LM-002", "FADR", 0.93, 0.90, "Fornecedores de roteirização (faixa 'forte' > 90%)", "C"),
    Meta("LM-001", "OTD vs. promessa", 0.96),
    Meta("LM-003", "Custo por entrega", 12.5, unidade="R$", polaridade="menor"),
    Meta("MK-002", "POAS", 1.80, unidade="x"),
    Meta("PE-003", "Turnover precoce (<90d)", 0.20, polaridade="menor"),
]


@dataclass
class ParametrosCapacidade:
    """Premissas do modelo de mix de recursos (mão de obra de CD)."""

    produtividade_pedidos_hh: float = 7.5  # pedidos por hora-homem, operador treinado
    horas_turno: float = 8.0
    dias_semana: int = 6
    custo_hh_proprio: float = 38.0  # R$/h, com encargos
    custo_hh_extra: float = 57.0  # +50%
    custo_hh_temporario: float = 46.0
    custo_pedido_3pl: float = 7.40  # R$/pedido, tudo incluído
    fator_produtividade_temp: float = 0.72  # curva de aprendizagem média no período
    acuracia: dict = field(
        default_factory=lambda: {"proprio": 0.9975, "extra": 0.9965, "temporario": 0.9945, "3pl": 0.9958}
    )
