# Lean Six Sigma — Programa e Governança de Master Black Belt

Dois níveis de medição:
1. **KPIs de processo** usados dentro dos projetos (capability, DPMO, rendimento).
2. **KPIs do programa** que o MBB gerencia como portfólio (resultado financeiro, pipeline, sustentação, formação).

## 1. KPIs de processo

| ID | KPI | Fórmula | Pol. | Nota |
|---|---|---|---|---|
| LS-001 | DPMO | Defeitos / (unidades × oportunidades) × 10⁶ | ↓ | Definição de "oportunidade" precisa ser padronizada, senão infla o sigma |
| LS-002 | Nível sigma | Z de longo prazo + 1,5 (convenção de shift) | ↑ | 3,4 DPMO ≈ 6σ na convenção com shift de 1,5 |
| LS-003 | Cp / Cpk | Cp = (LSE−LIE)/6σ; Cpk = min(LSE−μ, μ−LIE)/3σ | ↑ | ≥ 1,33 usual; ≥ 1,67 para características críticas (referência AIAG) |
| LS-004 | Ppk | Como Cpk com desvio padrão global (longo prazo) | ↑ | Ppk ≪ Cpk → processo instável |
| LS-005 | FPY | Unidades boas na 1ª passagem / unidades que entram (por etapa) | ↑ | |
| LS-006 | RTY | Π FPY de cada etapa | ↑ | Revela a "fábrica oculta" de retrabalho |
| LS-007 | OEE | Disponibilidade × Performance × Qualidade | ↑ | Para ativos: sorters, esteiras, AMRs |
| LS-008 | PCE (eficiência do ciclo) | Tempo de valor agregado / lead time total | ↑ | Em logística é comum < 10% |
| LS-009 | COPQ | Custo de falhas internas + externas + avaliação + prevenção (mensurável) | ↓ | Traduz qualidade para a linguagem do CFO |

**Exemplo logístico:** processo de expedição com 5 etapas, FPY de 98% em cada → RTY = 0,98⁵ ≈ 90,4%. Cerca de 1 em cada 10 pedidos passa por algum retrabalho, mesmo com "98% de qualidade" em cada etapa.

## 2. KPIs do programa (visão MBB)

```
North Star: Resultado financeiro validado por Finanças e sustentado em 12 meses (R$)
├── Resultado
│   ├── Hard savings validados (R$)                    [↑]
│   ├── Soft savings / cost avoidance (R$, separado)   [monitorar]
│   ├── ROI do programa (savings / custo do programa)  [↑]
│   └── Taxa de sustentação: projetos com ganho mantido aos 12 meses [↑]
├── Pipeline
│   ├── % projetos vinculados à X-Matrix/Hoshin       [↑]
│   ├── Cycle time DMAIC — GB e BB (dias)             [↓]
│   ├── Projetos parados em uma fase > 60 dias        [↓]
│   └── Tollgates no prazo                            [↑]
├── Capacitação
│   ├── Belts certificados / meta (por nível)         [↑]
│   ├── Projetos por belt ativo / ano                 [↑]
│   └── Retenção de BBs em 24 meses                   [↑]
└── Cultura
    ├── Kaizens / ideias implementadas por colaborador [↑]
    └── % líderes com gemba walk regular              [↑]
```

| ID | KPI | Fórmula | Nota |
|---|---|---|---|
| LS-101 | Hard savings validados | Σ savings aprovados por Finanças no P&L | Regra de validação escrita antes do projeto começar |
| LS-102 | Taxa de sustentação | Projetos com KPI no novo patamar aos 12 meses / projetos encerrados há 12 meses | A métrica que separa programa maduro de "teatro de melhoria" |
| LS-103 | Cycle time DMAIC | Dias entre charter aprovado e controle entregue | ⚠️ referência comum: GB 3–4 meses, BB 4–6 meses |
| LS-104 | Alinhamento estratégico | Projetos ligados a objetivo Hoshin / projetos ativos | |
| LS-105 | ROI do programa | Hard savings / custo total (horas de belts + treinamento + consultoria) | |
| LS-106 | Belts ativos | Belts com projeto em andamento / belts certificados | Belt certificado sem projeto é custo |

## OKRs de exemplo (programa LSS)

**O1 — Transformar o programa de melhoria em alavanca de P&L**
- KR1: R$ X milhões em hard savings validados por Finanças no semestre
- KR2: Taxa de sustentação aos 12 meses de 60% → 85%
- KR3: 90% dos projetos BB vinculados a objetivos da X-Matrix

**O2 — Acelerar o ciclo de melhoria**
- KR1: Cycle time de projetos BB de 7 → 4,5 meses
- KR2: Zero projetos parados > 60 dias na mesma fase
- KR3: 20 GBs certificados com projeto concluído (não só treinamento)

## SLAs do Escritório de Excelência Operacional

| SLA | SLI | Meta ⚠️ |
|---|---|---|
| Mentoria | Sessões de coaching MBB→BB realizadas / planejadas | 95% |
| Tollgate | Tollgates avaliados em ≤ 5 dias úteis da solicitação | 90% |
| Validação financeira | Savings validados por Finanças em ≤ 30 dias do encerramento | 90% |
| Suporte estatístico | Pedidos de análise respondidos em ≤ 3 dias úteis | 90% |

## Integração com as demais áreas
Cada KPI das pastas 01–07 que estiver **fora de controle estatístico de forma recorrente** é candidato natural a projeto DMAIC. Use o [catálogo](../../catalogo/kpis.csv) para priorizar por impacto (COPQ) × esforço.
