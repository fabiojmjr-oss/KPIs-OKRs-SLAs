# Caso integrado · Vértice Commerce & Logística (fictícia)

> Empresa, unidades e dados são **fictícios** e servem para estudo e demonstração. As referências de mercado (Mercado Livre, Amazon, WERC) são divulgações públicas, citadas com fonte em [`linha-de-base-mercado.md`](../00-fundamentos/linha-de-base-mercado.md). Não há afiliação com essas empresas.

## 1. Perfil
| Dimensão | Situação em jan/2025 | Situação em set/2026 |
|---|---|---|
| Porte | ~68 mil pedidos/dia, Sul e Sudeste | ~178 mil pedidos/dia fora de pico, 5 regiões |
| Modelo | Híbrido: CDs e bases próprios nas regiões maduras, 3PL na expansão | Idem, com 3PL em ~28% dos pedidos (KRI MM-010) |
| Rede | 7 CDs, 5 hubs, 12 bases de last mile (entrada de NE em abr, CO em jun e N em ago/2025) | +35% de capacidade e CDs regionais ampliados |
| Sistemas | ERP, WMS, TMS, app de entrega, CRM/SAC, plataformas de mídia, HRIS | Mesmos, com conferência por scanner e roteirização dinâmica |

## 2. Dor central
> **Equilibrar recursos materiais e humanos sem sacrificar o resultado financeiro nem os planos de futuro.**

Na prática, são três tensões simultâneas:
1. **Pico × custo fixo.** Dimensionar para a Black Friday deixa capacidade ociosa o ano inteiro; dimensionar para a média destrói o OTD em novembro.
2. **Próprio × terceiro.** O 3PL dá elasticidade e custo variável, mas tem acurácia menor e concentra risco (KRI).
3. **Hoje × 2027.** Cortar quadro após o pico melhora o ano, mas desmonta a capacidade necessária para a próxima onda de expansão.

A ferramenta para essa decisão é o modelo de mix de recursos ([`kpikit/capacidade.py`](../kpikit/capacidade.py)), exposto no app (aba *Capacidade*) e no notebook (seção 5).

## 3. X-Matrix (Hoshin Kanri)

```
                         ┌──────────────────────────────────────────┐
                         │   RUPTURAS 3–5 ANOS (Breakthrough)       │
                         │ B1 Top-3 em entrega nacional em até 48h  │
                         │ B2 Custo logístico/receita ≤ 9%          │
                         │ B3 Operação data-driven de ponta a ponta │
                         └──────────────────────────────────────────┘
┌─────────────────────────┐                          ┌──────────────────────────────┐
│ OBJETIVOS 2026          │        ◄── X ──►         │ PRIORIDADES DE MELHORIA      │
│ O1 Confiabilidade       │                          │ capacidade_2026 · cds_regionais│
│ O2 Expansão nacional    │                          │ wms_scanner · janelas_linehaul│
│ O3 Tecnologia de mercado│                          │ roteirizacao_eta · rede_pudo │
│ O4 Crescimento rentável │                          │ midia_poas · onboarding_buddy│
└─────────────────────────┘                          └──────────────────────────────┘
                         ┌──────────────────────────────────────────┐
                         │ MÉTRICAS (KRs) → ver okrs_2026.json      │
                         └──────────────────────────────────────────┘
```

### Matriz de correlação: iniciativas × objetivos (● forte · ○ fraca)

| Iniciativa (início) | O1 Confiab. | O2 Nacional | O3 Tecnologia | O4 Rentável | Dono |
|---|:-:|:-:|:-:|:-:|---|
| Plano de capacidade 2026 (jan) | ● | ● | | ○ | Planejamento |
| Onboarding com buddy (jan) | ○ | | | ● | RH + Operações |
| WMS com conferência por scanner (fev) | ○ | | ● | ○ | Supply Chain + TI |
| Malha com janelas sincronizadas (mar) | ● | ● | ○ | | Rede |
| Ampliação dos CDs de NE e CO (mar) | ○ | ● | | | Expansão |
| Roteirização dinâmica e ETA (abr) | ● | | ● | ○ | Last mile + TI |
| Mídia por POAS e incrementalidade (abr) | | | ○ | ● | Marketing |
| Rede PUDO/lockers (mai) | ● | | | ● | Last mile |

Cada iniciativa existe no simulador (`config.INICIATIVAS`) com efeito em rampa sobre os KPIs que deveria mover. Assim a hipótese do OKR pode ser verificada nos dados.

## 4. OKRs 2026
Definidos em [`okrs_2026.json`](okrs_2026.json) e **pontuados automaticamente** por `kpikit.okr.pontuar()`: linha de base no 2S25 e atual no 3T26.

| Obj. | Objetivo | KRs | Contrapeso |
|---|---|---|---|
| O1 | Ser a entrega em que o cliente confia sem acompanhar o rastreio | OTD 96% · FADR 93% · SAC ≤ 1,5/100 | Tentativa falsa ≤ 1% |
| O2 | Levar a promessa do Sudeste para o Brasil inteiro | 48h Brasil 80% · 48h NE 65% · OTD-p 99% | Custo/kg ≤ R$ 3,30 |
| O3 | CDs com padrão de classe mundial | Acurácia 99,68% · Dock-to-stock 4 h · Cut-off 99% | Produtividade ≥ 12 linhas/HH |
| O4 | Crescer com lucro e com gente que fica | POAS 1,8 · Custo/entrega R$ 12,50 · Turnover precoce 20% | Taxa de frequência ≤ 12 |

**Resultado em 3T26** (ver notebook): O1 0,72 · O2 0,84 · O3 0,84 · O4 0,73. O O2 **viola o contrapeso** por efeito mix geográfico, uma lição de governança sobre contrapesos não estratificados. No O4, o POAS subiu de 1,31 para 1,58, mas a meta de 1,80 segue **em risco**. E o POAS usa receita atribuída pela plataforma: o [notebook de marketing](../notebooks/marketing_mmm_incrementalidade.ipynb) mostra por que a alocação de verba precisa de ROAS **incremental**.

## 5. SLAs de interface (rede híbrida)

| SLA | Provedor → Cliente | SLI | Compromisso | SLO interno |
|---|---|---|---|---|
| Expedição | CD (próprio/3PL) → Middle mile | SC-009 | 98% | 99% |
| Acurácia | CD 3PL → Vértice | SC-007 | 99,55% | 99,60% |
| Transferência | Transportadora → Vértice | MM-002 (janela ±30 min) | 94% | 96% |
| Disponibilidade na base | Hub → Last mile | % volumes na base até a saída das rotas | 98% | 99% |
| Entrega | Operador LM 3PL → Vértice | LM-001 por faixa de CEP | 94% capitais / 88% interior | +1 p.p. |
| Evidência | Operador LM → Vértice | POD válido (geo + foto) | 99% | 99,5% |
| Calendário promocional | Marketing → S&OP | Aviso ≥ 21 dias com uplift estimado | 100% das campanhas > R$ 500 mil | — |
| Reposição de quadro | RH → Operações | Vagas preenchidas ≤ 15 dias | 90% | 95% |

**Regra de capability:** um SLA só é contratado quando o processo está sob controle estatístico e com Ppk ≥ 1,0 na meta. Pelo notebook, o CD-AM1 ainda não atende essa regra para dock-to-stock de 12 h.

## 6. Como adaptar por porte

| Porte | O que manter | O que simplificar |
|---|---|---|
| **Grande** (este caso) | Tudo: X-Matrix, OKRs por diretoria, CEP por unidade, otimização de mix, SLAs contratuais estratificados | — |
| **Médio** (1–3 CDs, frota mista) | 1 North Star por área, 3 OKRs corporativos, SLAs com transportadoras, CEP nos 3–5 KPIs críticos | Otimização vira planilha de cenários; mix constante só no custo de frete |
| **Pequeno** (1 CD, transportadoras) | OTD, FADR, acurácia, custo/pedido, turnover; 1 OKR por trimestre | Sem X-Matrix; cadência semanal única; SLA simples com a transportadora principal |
