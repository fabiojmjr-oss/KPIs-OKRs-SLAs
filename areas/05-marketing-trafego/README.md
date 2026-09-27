# Marketing — Campanhas de Tráfego (Mídia Paga)

## Mental model: do clique ao lucro
```
Receita = Investimento × (1/CPM) × CTR × Taxa de conversão × Ticket médio
Lucro   = Receita × Margem de contribuição − Investimento
```
A armadilha clássica é otimizar o funil de cima (CPM, CTR) e perder o de baixo (margem, recompra). **ROAS alto com margem baixa pode destruir valor.**

## Hierarquia de métricas

| Nível | Métricas | Quem olha |
|---|---|---|
| Negócio | Lucro incremental, MER (receita total / investimento total em mídia), LTV:CAC, payback de CAC | Diretoria / CFO |
| Aquisição | CAC (novos clientes), ROAS, POAS (lucro/gasto), CPA | Head de growth |
| Funil | Taxa de conversão, CPC, CTR, frequência, CPM | Analista de mídia |
| Qualidade | Taxa de recompra em 90 dias, % tráfego inválido, taxa de devolução do cliente adquirido | Growth + Ops |

## Árvore de KPIs

```
North Star: Lucro de contribuição incremental gerado por mídia (R$)
├── Eficiência
│   ├── MER (blended)                          [↑]
│   ├── ROAS / POAS por canal                  [↑] ⇄ contrapeso: % receita de novos clientes
│   └── CAC novos clientes                     [↓]
├── Valor do cliente
│   ├── LTV (margem) em 12 meses               [↑]
│   ├── LTV:CAC                                [↑]
│   └── Payback de CAC (meses)                 [↓]
├── Funil
│   ├── CTR                                    [↑ leading]
│   ├── Taxa de conversão (sessão → pedido)    [↑]
│   └── CPC / CPM                              [↓]
└── Verdade da medição
    ├── Incrementalidade (lift de testes geo/holdout) [↑]
    └── Divergência plataforma × analytics × ERP (%)  [↓]
```

## KPIs essenciais

| ID | KPI | Fórmula | Pol. | Nota |
|---|---|---|---|---|
| MK-001 | ROAS | Receita atribuída / investimento | ↑ | Atribuição da plataforma superestima; comparar com MER |
| MK-002 | POAS | Lucro bruto atribuído / investimento | ↑ | Corrige o viés do ROAS para produtos de margem baixa |
| MK-003 | MER | Receita total / investimento total em mídia | ↑ | Imune a disputas de atribuição |
| MK-004 | CAC | Investimento em aquisição / novos clientes | ↓ | Só novos clientes |
| MK-005 | LTV:CAC | LTV (margem) / CAC | ↑ | ⚠️ 3:1 é heurística popular (origem SaaS), não lei |
| MK-006 | Payback de CAC | CAC / margem mensal por cliente | ↓ | |
| MK-007 | CTR | Cliques / impressões | ↑ | Leading de criativo |
| MK-008 | Taxa de conversão | Pedidos / sessões | ↑ | Depende do site e da **promessa de entrega** |
| MK-009 | Lift incremental | (Conversões grupo exposto − controle) / controle | ↑ | Via geo-lift, holdout ou conversion lift |
| MK-010 | Divergência de dados | \|Receita plataforma − receita ERP\| / receita ERP | ↓ | Higiene de medição |

## Medição moderna (o que mudou)
- Perda de sinal (iOS ATT, restrições a cookies de terceiros) tornou a atribuição por último clique pouco confiável.
- A prática atual combina **MMM** (Marketing Mix Modeling — ferramentas abertas como Robyn, da Meta, e Meridian, do Google), **testes de incrementalidade** e atribuição de plataforma como sinal tático.
- Regra: plataforma para otimização diária; MMM + testes para alocação de orçamento.

## Conexão com logística (o elo que quase ninguém mede)
- **Frete e prazo na página de produto** são alavancas de conversão: promessa mais curta ↑ conversão.
- Campanha sem **comunicação ao planejamento** gera pico não previsto → ruptura, estouro de cut-off, queda de OTD → avaliação ruim → CAC futuro sobe.
- SLA interno recomendado abaixo (Marketing → Supply).

## OKRs de exemplo

**O1 — Crescer com lucro, não com volume**
- KR1: POAS blended de 1,1 → 1,5
- KR2: 30% do orçamento validado por teste de incrementalidade no trimestre
- KR3: CAC de novos clientes −15% mantendo ≥ 40% de receita vinda de novos

**O2 — Mídia sincronizada com a operação**
- KR1: 100% das campanhas > R$ X comunicadas ao S&OP com ≥ 21 dias
- KR2: Ruptura de SKUs anunciados ≤ 1%
- KR3: Zero campanhas ativas em SKUs sem estoque (automação de pausa por feed)

## SLAs

| SLA | Provedor → Cliente | SLI | Meta ⚠️ |
|---|---|---|---|
| Agência | Agência → Marca | Relatório semanal até D+1 útil; resposta a alterações ≤ 4h úteis | 95% |
| Setup de campanha | Mídia → Negócio | Campanhas no ar na data acordada com tracking validado | 98% |
| Previsão de demanda | Marketing → Supply/S&OP | Calendário promocional com uplift estimado enviado ≥ 21 dias antes | 100% campanhas relevantes |
| Feed de produtos | E-commerce → Mídia | SKUs sem estoque removidos do feed em ≤ 1h | 99% |
