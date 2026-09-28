# Gestão de Pessoas (foco em operações)

Em operação logística, **pessoas são a variável de capacidade mais volátil**: absenteísmo de 8% num turno de separação equivale a perder uma linha inteira. KPIs de pessoas aqui são tratados como KPIs de capacidade e risco — não só de RH.

## Mental model: Capacidade efetiva
```
Capacidade efetiva = Headcount × (1 − absenteísmo) × horas × produtividade × curva de aprendizagem
```
Turnover alto não custa só recrutamento: joga parte da equipe permanentemente no início da curva de aprendizagem.

## Árvore de KPIs

```
North Star: Capacidade efetiva disponível vs. planejada (%)
├── Disponibilidade
│   ├── Absenteísmo (%)                             [↓ leading]
│   ├── Turnover total e voluntário (% a.m.)        [↓]
│   ├── Turnover precoce (saídas < 90 dias)         [↓]  ← sinal de seleção/integração ruim
│   └── Aderência à escala                          [↑]
├── Aquisição
│   ├── Time-to-fill (dias)                         [↓]
│   ├── Qualidade da contratação (aprovados em 90d) [↑]
│   └── Custo por contratação                       [↓]
├── Desenvolvimento
│   ├── Tempo até proficiência (dias até 100% da meta de produtividade) [↓]
│   ├── Horas de treinamento por colaborador        [↑]
│   └── Cobertura de polivalência (matriz de habilidades) [↑]
├── Engajamento e liderança
│   ├── eNPS                                        [↑]
│   └── Sucessão: % posições-chave com sucessor pronto [↑]
└── Segurança e saúde
    ├── Taxa de frequência de acidentes (TF)        [↓]
    ├── Taxa de gravidade (TG)                      [↓]
    └── Riscos psicossociais mapeados e tratados (NR-1) [↑]
```

## KPIs essenciais

| ID | KPI | Fórmula | Pol. | Nota |
|---|---|---|---|---|
| PE-001 | Absenteísmo | Horas ausentes não programadas / horas programadas | ↓ | Separar justificado/injustificado; olhar por dia da semana |
| PE-002 | Turnover | Desligamentos no mês / headcount médio | ↓ | Separar voluntário × involuntário |
| PE-003 | Turnover precoce | Desligados com < 90 dias / admitidos no período (coorte) | ↓ | Medir por coorte de admissão |
| PE-004 | Time-to-fill | Dias entre abertura e aceite da vaga | ↓ | ⚠️ referências de mercado variam muito por cargo |
| PE-005 | Tempo até proficiência | Dias até atingir 100% do padrão de produtividade | ↓ | Liga RH à operação |
| PE-006 | Índice de polivalência | Pessoas habilitadas em ≥ 2 funções / headcount | ↑ | Chave para absorver pico e absenteísmo |
| PE-007 | eNPS | % promotores (9–10) − % detratores (0–6) | ↑ | Escala −100 a +100 |
| PE-008 | Taxa de frequência | Nº acidentes com e sem afastamento × 1.000.000 / horas-homem trabalhadas | ↓ | Conforme ABNT NBR 14280 |
| PE-009 | Taxa de gravidade | Dias perdidos/debitados × 1.000.000 / horas-homem trabalhadas | ↓ | NBR 14280 |
| PE-010 | Sucessão | Posições-chave com sucessor "pronto agora" / posições-chave | ↑ | |
| PE-011 | Cobertura da escala | Presentes esperados / operadores necessários, por dia | ↑ | Abaixo de 100% = pedido fora do cut-off |
| PE-012 | Ociosidade da escala | (Presentes − necessários) / presentes | ↓ | Contrapeso do PE-011 |
| PE-013 | Retenção em 90 dias | S(90) da curva de Kaplan-Meier dos admitidos | ↑ | Trata censura; complementa PE-003 |

> **Ferramentas:** previsão de absenteísmo, curva de retenção (Kaplan-Meier + regressão logística) e escala 6x1 por programação inteira em [`kpikit/pessoas.py`](../../kpikit/pessoas.py), explicadas passo a passo em [`notebooks/pessoas_forca_de_trabalho.ipynb`](../../notebooks/pessoas_forca_de_trabalho.ipynb).

## Contexto regulatório (Brasil)
- ⚠️ A **NR-1** atualizada (Portaria MTE nº 1.419/2024) incluiu os **riscos psicossociais** no Gerenciamento de Riscos Ocupacionais (GRO/PGR); a fiscalização punitiva foi adiada para maio de 2026. Em operações com metas de produtividade agressivas, turnos noturnos e pressão de pico, isso cria um KPI de **conformidade** novo — e um argumento para metas sustentáveis. Validar status com o SESMT/jurídico.

## OKRs de exemplo

**O1 — Estabilizar a força de trabalho antes do pico**
- KR1: Turnover precoce (< 90 dias) de 35% → 20%
- KR2: Tempo até proficiência de 21 → 12 dias (trilha de onboarding padronizada + buddy)
- KR3: Índice de polivalência de 25% → 45%

**O2 — Liderança de primeira linha que retém**
- KR1: eNPS nas unidades com pior resultado de −10 → +15
- KR2: 100% dos supervisores certificados no programa de liderança operacional
- KR3: Absenteísmo injustificado de 4,5% → 2,5%

## SLAs internos (RH ↔ Operação)

| SLA | SLI | Meta ⚠️ |
|---|---|---|
| Reposição | Vagas operacionais preenchidas em até N dias da requisição | 90% em ≤ 15 dias |
| Temporários de pico | Temporários disponíveis na data / solicitados com antecedência ≥ 30 dias | 95% |
| Folha e benefícios | Erros de folha por 1.000 colaboradores | ≤ 2 |
| Atendimento ao colaborador | Chamados de RH resolvidos em até 48h | 90% |
