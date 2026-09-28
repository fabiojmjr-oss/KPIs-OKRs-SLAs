# Supply Chain — Planejamento, Estoque e Armazenagem (CD)

## Framework de referência: SCOR (ASCM)
O modelo SCOR (hoje *SCOR Digital Standard*, mantido pela ASCM) organiza o desempenho em atributos. Use-os como "gavetas" para garantir equilíbrio do painel:

| Atributo | Métrica nível 1 (SCOR) | O que protege |
|---|---|---|
| Confiabilidade | Perfect Order Fulfillment | Cliente |
| Responsividade | Order Fulfillment Cycle Time | Cliente |
| Agilidade | Adaptabilidade de supply (upside/downside) | Resiliência |
| Custo | Total Cost to Serve | Margem |
| Eficiência de ativos | Cash-to-Cash Cycle Time, Retorno sobre ativos fixos | Caixa |

## Árvore de KPIs

```
North Star: Pedido Perfeito (%)  = no prazo × completo × sem avaria × documentação correta
├── Planejamento
│   ├── Acurácia de forecast (1 − WMAPE)            [leading]
│   ├── Viés de forecast (Bias)                      [leading]
│   └── Aderência ao plano S&OP                      [leading]
├── Estoque
│   ├── Cobertura de estoque (dias)                  [↓/faixa]
│   ├── Nível de serviço / Fill rate por linha       [↑]
│   ├── Ruptura (OOS) em SKUs A                      [↓]
│   └── Acurácia de inventário (IRA)                 [↑]
├── Armazenagem (CD)
│   ├── Dock-to-stock (h)                            [↓]
│   ├── Acurácia de picking                          [↑]
│   ├── Produtividade (linhas/HH)                    [↑]  ⇄ contrapeso: acurácia
│   ├── % pedidos expedidos até o cut-off            [↑ leading de OTD]
│   └── Ocupação de posições (%)                     [faixa 80–90%]
└── Custo e caixa
    ├── Custo logístico / receita líquida (%)        [↓]
    ├── Custo por pedido expedido (R$)               [↓]
    └── Cash-to-cash (dias)                          [↓]
```

## KPIs essenciais

| ID | KPI | Fórmula | Pol. | Referência |
|---|---|---|---|---|
| SC-001 | Pedido perfeito | Pedidos sem nenhuma falha / pedidos totais | ↑ | Produto das 4 dimensões — por isso sempre é menor que qualquer componente isolado |
| SC-002 | Acurácia de forecast | 1 − Σ\|real − previsto\| / Σ real (WMAPE) | ↑ | Medir no horizonte de lead time, não no mês corrente |
| SC-003 | Bias | Σ(previsto − real) / Σ real | faixa ±5% | Bias persistente é pior que erro aleatório |
| SC-004 | Fill rate (linha) | Linhas atendidas completas / linhas pedidas | ↑ | |
| SC-005 | Acurácia de inventário | Posições sem divergência / posições contadas | ↑ | ⚠️ best-in-class ≥ 99,5% (WERC DC Measures — validar edição) |
| SC-006 | Dock-to-stock | Tempo médio (P90) entre chegada na doca e disponível para venda | ↓ | Usar P90, não média |
| SC-007 | Acurácia de picking | Linhas corretas / linhas separadas | ↑ | ⚠️ best-in-class ≥ 99,9% (WERC) |
| SC-008 | Produtividade de picking | Linhas separadas / horas-homem diretas | ↑ | Contrapeso obrigatório: SC-007 |
| SC-009 | Expedição no cut-off | Pedidos expedidos até o cut-off / pedidos elegíveis | ↑ | Principal leading do OTD de transporte |
| SC-010 | Custo logístico / receita | Custo total de logística / receita líquida | ↓ | Comparar só dentro do mesmo setor/mix |
| SC-011 | Cash-to-cash | DSI + DSO − DPO | ↓ | |

## OKRs de exemplo

**O1 — Tornar o CD à prova de pico (Black Friday / Natal)**
- KR1: Expedição no cut-off em dias de pico de 82% → 97% *(committed)*
- KR2: Capacidade sustentada de 45k → 70k pedidos/dia sem hora extra acima de 15% *(aspirational)*
- KR3: Acurácia de picking ≥ 99,8% durante todo o período de pico *(contrapeso transformado em KR)*

**O2 — Liberar caixa sem sacrificar disponibilidade**
- KR1: Cobertura de estoque de 62 → 45 dias
- KR2: Ruptura em SKUs curva A ≤ 2% (hoje 3,5%)
- KR3: WMAPE nível SKU-semana de 38% → 28%

## SLAs típicos

| SLA | Provedor → Cliente | SLI | Meta ⚠️ |
|---|---|---|---|
| Recebimento | CD → Compras/Comercial | % NFs com dock-to-stock ≤ 24h | 95% |
| Expedição | CD → Transporte | % pedidos liberados ≤ 2h antes do cut-off expedidos no dia | 98% |
| Acurácia | 3PL → Embarcador | Acurácia de inventário (inventário rotativo mensal) | 99,5% |
| Forecast | Comercial → Supply | Envio do forecast até D-X com WMAPE ≤ Y | *contrapartida do cliente* |

## Caso de mercado
- **Mercado Livre** usa o *fulfillment* próprio para controlar o cut-off e a promessa de prazo — a empresa reporta trimestralmente a proporção de entregas em até 48h no Brasil como indicador estratégico de negócio (ver releases de resultados MELI). Lição: o KPI operacional do CD vira argumento comercial quando conectado à promessa ao cliente.
