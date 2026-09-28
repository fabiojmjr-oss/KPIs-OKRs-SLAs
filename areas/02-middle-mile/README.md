# Middle Mile — Transferência, Line-haul e Hubs de Triagem

Middle mile é o elo entre CD/fulfillment e as bases de last mile: rotas de transferência (line-haul), cross-docking e centros de triagem (sorting). É onde **o prazo é consumido invisivelmente** — um atraso de 2h numa carreta que perde a janela do hub vira D+1 no cliente.

## Mental model: a rede como relógio
A malha funciona por **janelas sincronizadas** (cut-off de CD → partida → chegada no hub → onda de triagem → partida para base). O KPI mais importante não é velocidade; é **aderência à janela**. Mede-se em *on-time departure* (OTD-p) e *on-time arrival* (OTA), porque chegar cedo demais também desorganiza doca.

## Árvore de KPIs

```
North Star: % volume que chega na base de last mile dentro da janela planejada
├── Transporte (line-haul)
│   ├── On-time departure (OTD-p)                    [leading]
│   ├── On-time arrival (OTA)                        [lagging]
│   ├── Ocupação de veículo (peso e cubagem)         [↑]  ⇄ contrapeso: OTA
│   ├── Custo por kg (ou por volume) transferido     [↓]
│   └── Empty miles / km vazio (%)                   [↓]
├── Hub / cross-dock
│   ├── Dwell time (tempo de permanência, P90)       [↓]
│   ├── Taxa de missort (triagem incorreta)          [↓]
│   ├── Produtividade de triagem (volumes/HH)        [↑]
│   ├── Backlog no fechamento da onda                [↓ leading]
│   └── Tempo de giro de doca (turn time)            [↓]
└── Qualidade e risco
    ├── Avaria / extravio por 10k volumes            [↓]
    └── Dependência de transportadora (% volume top-1) [KRI]
```

## KPIs essenciais

| ID | KPI | Fórmula | Pol. | Nota |
|---|---|---|---|---|
| MM-001 | On-time departure | Partidas até a hora planejada + tolerância / partidas | ↑ | Tolerância explícita (ex.: 15 min) |
| MM-002 | On-time arrival | Chegadas dentro da janela / chegadas | ↑ | Janela com limite inferior e superior |
| MM-003 | Ocupação de veículo | Carga embarcada / capacidade (a restrição ativa: peso **ou** cubagem) | ↑ | Medir na restrição que "estoura" primeiro |
| MM-004 | Custo por kg transferido | Custo de frete de transferência / kg | ↓ | Separar fixo (dedicado) de variável (spot) |
| MM-005 | Dwell time P90 | Percentil 90 do tempo entrada→saída do volume no hub | ↓ | Média esconde volumes "esquecidos" |
| MM-006 | Missort | Volumes triados para destino errado / volumes triados | ↓ | Medido por PPM é mais sensível |
| MM-007 | Backlog na onda | Volumes não triados ao fechar a onda | ↓ | Principal leading do OTA seguinte |
| MM-008 | Avaria/extravio | Ocorrências / 10.000 volumes | ↓ | |
| MM-009 | Km vazio | Km sem carga / km total | ↓ | Alavanca de backhaul |

## Trade-off central
**Ocupação × Pontualidade.** Esperar encher a carreta melhora custo e destrói janela. A regra de decisão deve estar escrita: *"a carreta sai no horário com qualquer ocupação; se ocupação < X% por N dias, a rota é redesenhada"*. Isso tira a decisão do improviso do turno.

## OKRs de exemplo

**O1 — Sincronizar a malha Sudeste para viabilizar D+1**
- KR1: OTD-p das linhas CD→hubs de 78% → 95%
- KR2: Dwell time P90 no hub principal de 9h → 5h
- KR3: Backlog na última onda ≤ 1% do volume do dia
- Contrapeso: custo por kg não sobe mais de 3%

**O2 — Reduzir custo de transferência com inteligência de rede**
- KR1: Ocupação média (restrição ativa) de 68% → 80%
- KR2: Km vazio de 22% → 14% via backhaul/rotas triangulares
- KR3: Spot < 10% do volume em dias não-pico

## SLAs típicos

| SLA | Provedor → Cliente | SLI | Meta ⚠️ |
|---|---|---|---|
| Transferência | Transportadora → Embarcador | OTA na janela ±30 min | 95% |
| Triagem | Hub → Bases de last mile | % volumes disponíveis na base até H de saída das rotas | 98% |
| Qualidade | Transportadora → Embarcador | Avaria + extravio ≤ N/10k volumes | contratual |
| Disponibilidade de frota | Transportadora → Embarcador | Veículos disponibilizados / solicitados com D-1 | 98% |

## Ferramentas
[`kpikit/middle_mile.py`](../../kpikit/middle_mile.py): consolidação 2D (peso × m³, heurística FFD e ótimo por MILP), mix de frota, simulação da política de despacho (esperar encher × sair no horário) e roteirização milk run (Clarke-Wright + 2-opt) com dimensionamento de veículo por rota e custo de jornada, e **desenho de rede com satélites de transbordo** (enumeração de configurações, custo × janela de entrega, onda antecipada e ponto de virada do custo fixo). Explicado passo a passo em [`notebooks/middle_mile_consolidacao_rotas.ipynb`](../../notebooks/middle_mile_consolidacao_rotas.ipynb) e interativo na aba *Middle mile* do app.

| ID | KPI | Fórmula | Pol. | Nota |
|---|---|---|---|---|
| MM-011 | Paradas por rota | Paradas / rotas | ↑ | Contrapeso: MM-013 |
| MM-012 | Volume despachado no prazo do hub | m³ que saem no prazo interno / m³ recebidos | ↑ | Mede a política de despacho |
| MM-013 | Rotas acima da jornada | Rotas com pernoite ou dupla / rotas | ↓ | Limite de serviço e de conformidade |

## Caso de mercado
- **Mercado Livre** montou malha aérea própria (Meli Air, em parceria com companhias aéreas) e dezenas de centros de *cross-docking/service centers* para encurtar o middle mile — a decisão de verticalizar veio de o middle mile ser o gargalo do prazo, não o last mile. ⚠️ Detalhes de frota e número de hubs mudam trimestralmente; conferir relatório vigente.
