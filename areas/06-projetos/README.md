# Gestão de Projetos e Portfólio

## Mental model: entregar o projeto ≠ capturar o benefício
O "triângulo de ferro" (prazo, custo, escopo) mede **eficiência de entrega**. O que a diretoria compra é **benefício realizado**. Um portfólio saudável mede os dois — e mede o benefício *depois* do encerramento do projeto.

Referências: PMBOK Guide (PMI) — abordagem por princípios e domínios de desempenho; ⚠️ PMI publicou nova edição recentemente, validar edição adotada na organização. Earned Value conforme ANSI/EIA-748.

## Árvore de KPIs

```
North Star: Valor realizado do portfólio vs. business case (%)
├── Estratégia
│   ├── % investimento em projetos alinhados a objetivos estratégicos [↑]
│   └── Taxa de projetos cancelados cedo (kill rate saudável) [faixa]
├── Entrega (Earned Value)
│   ├── SPI = EV / PV                           [↑ alvo ≥ 0,95]
│   ├── CPI = EV / AC                           [↑ alvo ≥ 0,95]
│   ├── EAC = BAC / CPI (previsão no término)   [↓]
│   └── TCPI (eficiência necessária para terminar no orçamento) [alerta se > 1,1]
├── Qualidade e risco
│   ├── Riscos altos sem plano de resposta      [↓]
│   ├── Mudanças de escopo aprovadas (%)        [monitorar]
│   └── Defeitos/pendências no aceite           [↓]
└── Benefícios
    ├── Benefício realizado em 6/12 meses / previsto [↑]
    └── Satisfação do patrocinador               [↑]
```

## KPIs essenciais

| ID | KPI | Fórmula | Pol. | Nota |
|---|---|---|---|---|
| PJ-001 | SPI | EV / PV | ↑ | < 0,9 → alerta; perde poder preditivo no fim do projeto (usar Earned Schedule) |
| PJ-002 | CPI | EV / AC | ↑ | CPI tende a estabilizar cedo (~20% de execução) — bom preditor |
| PJ-003 | EAC | BAC / CPI | ↓ | Versão simples; há variantes com SPI |
| PJ-004 | TCPI | (BAC − EV) / (BAC − AC) | ↓ | > 1,1 indica meta de custo irrealista |
| PJ-005 | Benefício realizado | Benefício medido / benefício do business case | ↑ | Medir 6 e 12 meses pós go-live |
| PJ-006 | Marcos no prazo | Marcos concluídos na data de baseline / marcos previstos | ↑ | Simples e comunicável |
| PJ-007 | Riscos altos sem resposta | Nº riscos (P×I alto) sem plano/dono | ↓ | |
| PJ-008 | Alinhamento estratégico | Capex/Opex em projetos vinculados à X-Matrix / total | ↑ | |

## OKRs de exemplo (PMO)

**O1 — Portfólio que entrega valor, não só cronograma**
- KR1: 100% dos projetos > R$ 500k com baseline de benefício validada por Finanças
- KR2: Benefício realizado aos 12 meses de 55% → 80% do business case
- KR3: Encerrar ou repriorizar 100% dos projetos com CPI < 0,8 por 2 meses

**O2 — Previsibilidade**
- KR1: % projetos com SPI ≥ 0,95 de 48% → 75%
- KR2: Desvio médio entre data prevista e real de 45 → 15 dias

## SLAs do PMO

| SLA | SLI | Meta ⚠️ |
|---|---|---|
| Status report | Atualização de EV e riscos até D+2 útil do fechamento | 100% |
| Change request | Decisão de comitê em ≤ 10 dias úteis | 90% |
| Gate review | Gates realizados na data com documentação completa | 95% |
