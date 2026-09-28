# Hierarquia: Estratégia → OKR → KPI → SLA

## 1. Definições operacionais

| Conceito | Pergunta que responde | Horizonte | Natureza | Exemplo logístico |
|---|---|---|---|---|
| **Objetivo estratégico** | Para onde vamos? | 3–5 anos | Direção | "Ser referência em entrega D+1 no Sudeste" |
| **OKR** | O que precisa *mudar* neste ciclo? | Trimestre / semestre | Transformação, ambição | O: Tornar o D+1 confiável · KR: OTD D+1 de 88% → 95% |
| **KPI** | O sistema está saudável? | Contínuo | Monitoramento, controle | OTD, custo por pedido, acurácia de picking |
| **SLA** | O que uma parte *garante* à outra? | Contrato / acordo | Compromisso com consequência | "95% das coletas até 14h, janela mensal, crédito de 2% por p.p. abaixo" |
| **SLO / SLI** | Qual o alvo interno e como medimos? | Contínuo | Engenharia do SLA | SLI = % coletas ≤14h; SLO interno = 97% (folga sobre o SLA de 95%) |
| **KRI** | Qual risco está crescendo? | Contínuo | Alerta antecipado | % volume concentrado em 1 transportadora |

**Regra de ouro:** SLO interno sempre mais apertado que o SLA externo. A diferença é o *buffer de erro* — conceito do Google SRE (error budget) aplicado à operação.

## 2. Como os três se conectam

```
Estratégia (Hoshin / X-Matrix)
   └── OKR (o que muda no ciclo) ──► move um KPI de patamar
          └── KPI (saúde do sistema) ──► quando estabiliza no novo patamar, vira base do SLA
                 └── SLA (compromisso entre partes) ──► medido por SLI, protegido por SLO
```

- Um **KR bem escrito é quase sempre um KPI em movimento** ("de X para Y").
- Quando o KR é atingido e estabilizado (controle estatístico), ele **sai do OKR e vai para o painel de KPIs** — e, se houver cliente interno/externo, **vira SLA**.
- Se um KPI crítico sai de controle, ele pode **entrar no OKR** do ciclo seguinte (modo "consertar").

## 3. Tipos de indicador

| Tipo | Definição | Uso |
|---|---|---|
| **Lagging** (resultado) | Mede o que já aconteceu | Prestação de contas: OTD, NPS, EBITDA logístico |
| **Leading** (direcionador) | Antecipa o resultado | Gestão diária: backlog às 10h, % pedidos liberados até o cut-off, absenteísmo do turno |
| **Contrapeso** | Impede otimização local | Produtividade ↔ acurácia; custo por entrega ↔ first attempt |
| **Vaidade** | Parece bom, não orienta decisão | Impressões de anúncio sem conversão; "pacotes movimentados" sem custo/qualidade |

## 4. Critérios de qualidade

**KPI — SMART + 4 testes executivos**
1. *Teste da decisão:* se o número mudar, alguém muda uma ação? Se não, é vaidade.
2. *Teste do dono:* existe um nome (não uma área) responsável?
3. *Teste da fonte:* dado vem de sistema transacional (WMS/TMS/ERP) sem planilha intermediária?
4. *Teste do contrapeso:* existe métrica que detecte o "jogo" desta?

**OKR — padrão Doerr / Google**
- 1–3 Objetivos por time; 2–4 KRs por Objetivo.
- KR mensurável, com linha de base, meta e data. Nunca uma tarefa ("implantar WMS" é iniciativa, não KR).
- Distinguir **committed** (esperado 1.0) de **aspirational** (0,6–0,7 é sucesso).
- OKR não entra na avaliação de desempenho/bônus individual — senão vira meta conservadora.

**SLA — 8 cláusulas mínimas**
1. Serviço e escopo · 2. SLI (fórmula exata) · 3. Meta · 4. Janela de medição · 5. Fonte de dados e quem mede · 6. Exclusões (força maior, dado do cliente errado) · 7. Consequência (crédito, plano de ação, escalonamento) · 8. Revisão periódica.

## 5. Anti-padrões mais frequentes

| Anti-padrão | Sintoma | Correção |
|---|---|---|
| Painel-cemitério | 60+ indicadores, reunião sem decisão | Máx. 5–7 KPIs por nível; restante vira drill-down |
| OKR = lista de projetos | KRs "entregar X" | Reescrever como resultado mensurável |
| Média escondendo cauda | OTD médio 96%, mas 1 região a 78% | Usar percentis (P90/P95) e estratificação |
| SLA sem exclusões | Discussão eterna de "culpa" | Definir exclusões e árbitro do dado previamente |
| Meta sem capacidade de processo | Meta 99% em processo com Cpk 0,7 | Meta derivada de capability + plano de melhoria (DMAIC) |
| Goodhart | Motorista marca "cliente ausente" para bater prazo | Contrapeso: auditoria de tentativa com geolocalização/foto |
