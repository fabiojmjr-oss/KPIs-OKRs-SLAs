# Last Mile — Entrega ao Cliente Final

A etapa mais cara e mais visível da cadeia. ⚠️ Estudo do Capgemini Research Institute (*The last-mile delivery challenge*, 2019) estimou o last mile em ~41% do custo total da cadeia de suprimentos — use como ordem de grandeza, não como meta.

## Mental model: custo por entrega é consequência da densidade e do first attempt
```
Custo por entrega ≈ Custo da rota / Entregas bem-sucedidas
                  ≈ (custo fixo do veículo + motorista) / (paradas × taxa de sucesso na 1ª tentativa)
```
Duas alavancas dominam: **densidade** (paradas por rota/hora) e **first attempt delivery rate (FADR)**. Uma redelivery pode custar tanto quanto a primeira tentativa — e ainda gera contato no SAC.

## Árvore de KPIs

```
North Star: Entrega no prazo prometido, na 1ª tentativa, sem ocorrência (% pedidos)
├── Serviço
│   ├── OTD — On-time delivery vs. promessa        [↑]
│   ├── FADR — Sucesso na 1ª tentativa             [↑]
│   ├── Taxa de ocorrência (avaria/extravio)       [↓]
│   └── Contatos no SAC por 100 pedidos            [↓]
├── Produtividade
│   ├── Paradas por hora (SPH)                     [↑] ⇄ contrapeso: FADR
│   ├── Paradas por rota                           [↑]
│   ├── Aderência à roteirização                   [↑]
│   └── Saída de rotas no horário (dispatch)       [↑ leading]
├── Custo
│   ├── Custo por entrega bem-sucedida (CPD)       [↓]
│   ├── Custo por pacote                           [↓]
│   └── % entregas via PUDO/lockers                [↑]
└── Pessoas e risco
    ├── Retenção de entregadores (30/90 dias)      [↑]
    ├── Sinistros por 1 milhão de km               [↓]
    └── Tentativas falsas (auditoria geo/foto)     [↓ contrapeso]
```

## KPIs essenciais

| ID | KPI | Fórmula | Pol. | Nota |
|---|---|---|---|---|
| LM-001 | OTD vs. promessa | Pedidos entregues até a data prometida / pedidos com data prometida vencida no período | ↑ | Denominador por **data prometida**, não por data de entrega (evita esconder atrasos) |
| LM-002 | FADR | Entregas com sucesso na 1ª tentativa / pacotes em rota | ↑ | |
| LM-003 | Custo por entrega bem-sucedida | Custo total da operação LM / entregas concluídas | ↓ | |
| LM-004 | Paradas por hora | Paradas realizadas / horas em rota | ↑ | Contrapeso LM-002 |
| LM-005 | Saída no horário | Rotas despachadas até H / rotas planejadas | ↑ | Leading do OTD do dia |
| LM-006 | Ocorrências | (Avarias + extravios) / 10.000 pacotes | ↓ | |
| LM-007 | Contatos por pedido | Contatos SAC ligados a entrega / 100 pedidos | ↓ | "Where is my order" é sintoma de previsibilidade ruim |
| LM-008 | Tentativa falsa | Tentativas sem evidência válida (geo fora do raio, sem foto) / tentativas malsucedidas | ↓ | Anti-Goodhart |
| LM-009 | Retenção de entregadores | Ativos no D+90 / iniciados no período | ↑ | Alta rotatividade derruba SPH e FADR |
| LM-010 | % PUDO/locker | Entregas em pontos de retirada / total | ↑ | Alavanca estrutural de densidade |

## OKRs de exemplo

**O1 — Acertar de primeira**
- KR1: FADR de 89% → 95%
- KR2: Contatos "onde está meu pedido" de 6 → 3 por 100 pedidos (via ETA dinâmico e notificação proativa)
- KR3: Tentativa falsa < 0,5%
- Contrapeso: SPH não cai mais de 5%

**O2 — Densificar a rede urbana**
- KR1: Entregas via PUDO/lockers de 4% → 12% nas capitais
- KR2: Custo por entrega bem-sucedida −12%
- KR3: Paradas por rota +15% com mesma frota

## SLAs típicos

| SLA | Provedor → Cliente | SLI | Meta ⚠️ |
|---|---|---|---|
| Prazo | Transportadora/operador → Embarcador | OTD vs. promessa, por região/faixa de CEP | 95–97% capitais; menor e estratificado no interior |
| First attempt | Operador → Embarcador | FADR | 92–95% |
| Evidência de entrega | Operador → Embarcador | % entregas com POD digital válido (geo + foto/assinatura) | 99% |
| Retorno/devolução | Operador → Embarcador | Devoluções retornadas ao CD em até N dias úteis | 95% |
| Tratativa de ocorrência | Operador → SAC | Ocorrências respondidas em até 24h | 95% |

> SLA de last mile **tem que ser estratificado** por região/faixa de CEP e área de risco. Um SLA nacional único ou é frouxo nas capitais ou impossível no interior.

## Casos de mercado
- **Amazon, Magalu, Mercado Livre** investiram em redes de pontos de retirada e entregadores parceiros para atacar densidade e FADR — o modelo "crowdsourced" traz elasticidade no pico, mas eleva o desafio de retenção (LM-009) e de conformidade (LM-008).
- **Correios**: prazos de serviço (SEDEX/PAC) são publicados por origem–destino; é um exemplo de promessa estratificada por matriz de CEP. ⚠️ Verificar tabela vigente no site oficial.
