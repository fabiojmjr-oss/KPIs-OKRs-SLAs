# Scrum e Agilidade

## Princípio
O Scrum Guide (2020) define três compromissos: **Product Goal**, **Sprint Goal** e **Definition of Done**. Ele não prescreve velocity como métrica de desempenho — usar velocity para comparar times ou cobrar produtividade é o anti-padrão mais comum. Meça **valor e fluxo**, não esforço.

## Frameworks de medição
| Framework | Foco | Métricas |
|---|---|---|
| **EBM** (Evidence-Based Management, Scrum.org) | Valor | 4 áreas-chave: Valor Atual, Valor Não Realizado, Tempo para o Mercado, Capacidade de Inovar |
| **Métricas de fluxo** (Kanban) | Previsibilidade | Throughput, cycle time, WIP, idade do item em andamento |
| **DORA** (DevOps Research and Assessment) | Entrega de software | Frequência de deploy, lead time para mudanças, taxa de falha de mudança, tempo de recuperação de deploy com falha |
| **OKR** | Resultado | Outcomes do Product Goal |

## Árvore de KPIs

```
North Star: Outcome do Product Goal (métrica de valor para o cliente/negócio)
├── Valor (EBM)
│   ├── Valor atual: satisfação/uso das funcionalidades entregues [↑]
│   ├── % funcionalidades usadas regularmente     [↑]
│   └── Sprint Goal atingido (%)                   [↑]
├── Fluxo
│   ├── Cycle time P85 (dias)                      [↓]
│   ├── Throughput (itens/semana)                  [estável]
│   ├── WIP vs. limite                             [≤ limite]
│   └── Idade do item mais antigo em andamento     [↓ leading]
├── Qualidade
│   ├── Taxa de falha de mudança (DORA)            [↓]
│   ├── Defeitos escapados para produção           [↓]
│   └── % tempo em trabalho não planejado          [↓]
└── Time
    ├── Previsibilidade: planejado × entregue (faixa 80–100%) [faixa]
    └── Saúde do time (pesquisa curta pós-retro)   [↑]
```

## KPIs essenciais

| ID | KPI | Fórmula | Pol. | Nota |
|---|---|---|---|---|
| AG-001 | Sprint Goal atingido | Sprints com goal atingido / sprints | ↑ | Mais honesto que "pontos entregues" |
| AG-002 | Cycle time P85 | Percentil 85 do tempo início→done | ↓ | Permite previsão probabilística ("85% dos itens em ≤ N dias") |
| AG-003 | Throughput | Itens concluídos / semana | estável | Base para Monte Carlo de datas |
| AG-004 | WIP | Itens em andamento | ≤ limite | Lei de Little: cycle time = WIP / throughput |
| AG-005 | Frequência de deploy | Deploys em produção / período | ↑ | DORA |
| AG-006 | Lead time para mudanças | Commit → produção | ↓ | DORA |
| AG-007 | Taxa de falha de mudança | Deploys que causam incidente / deploys | ↓ | DORA |
| AG-008 | Tempo de recuperação | Tempo para restaurar serviço após deploy com falha | ↓ | DORA |
| AG-009 | Trabalho não planejado | Horas em itens fora do sprint / horas totais | ↓ | |
| AG-010 | Uso de funcionalidades | Features com uso recorrente / features entregues | ↑ | EBM — Valor Atual |

## Aplicação em operações (não só software)
Scrum/Kanban funcionam bem em **times de melhoria contínua e implantação** (ex.: rollout de WMS em 12 CDs, abertura de novas bases de last mile). Nesse caso:
- Product Goal = "12 CDs operando no novo WMS com acurácia ≥ 99,8%"
- Incremento = 1 CD estabilizado (Definition of Done inclui 2 semanas de KPIs dentro do limite de controle)
- Métrica de fluxo = cycle time por CD implantado → previsibilidade do rollout

## OKRs de exemplo

**O1 — Previsibilidade que o negócio confia**
- KR1: Cycle time P85 de 18 → 9 dias
- KR2: Sprint Goal atingido de 50% → 80%
- KR3: Trabalho não planejado < 15%

**O2 — Entregar valor, não funcionalidades**
- KR1: 100% dos itens de backlog top-10 com hipótese de valor e métrica de sucesso
- KR2: Uso recorrente de funcionalidades entregues de 40% → 65%

## SLAs (classes de serviço Kanban)

| Classe | SLI | Meta ⚠️ |
|---|---|---|
| Expedite (incidente crítico) | Tempo até resolução | 85% em ≤ 24h |
| Data fixa | Entregue até a data compromissada | 95% |
| Padrão | Cycle time | 85% em ≤ N dias (N = P85 histórico) |
| Intangível (dívida técnica) | Capacidade reservada | ≥ 15% da capacidade |
