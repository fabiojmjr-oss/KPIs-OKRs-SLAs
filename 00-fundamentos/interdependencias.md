# Mapa de interdependências entre áreas

KPIs são desenhados por área, mas os resultados são produzidos pela **cadeia**. Este mapa mostra onde o KPI de uma área é o *leading indicator* de outra — e, portanto, onde precisam existir SLAs internos.

## Cadeia de causa e efeito (exemplo: campanha de Black Friday)

```
Marketing            Supply / CD           Middle mile            Last mile             Cliente
─────────            ───────────           ───────────            ─────────             ───────
Calendário promo ──► Forecast (WMAPE) ──► Plano de capacidade ──► Rotas/entregadores ──► OTD, FADR
MK: aviso ≥21d       SC-002                de linhas/hubs         LM-005, LM-009         LM-001
                     │                     MM-001                 │                      │
                     ▼                     │                      ▼                      ▼
Pessoas ───────────► Temporários + polivalência (PE-006) ─────────► Produtividade ────► NPS / recompra
                                                                                         │
                     ◄────────────────── CAC futuro sobe se a entrega falha ◄─────────────┘
```

## Matriz de SLAs internos recomendados

| Provedor ↓ / Cliente → | Supply/CD | Middle mile | Last mile | Marketing | Pessoas |
|---|---|---|---|---|---|
| **Marketing** | Calendário + uplift ≥ 21d | — | Volume por região ≥ 14d | — | — |
| **Supply/CD** | — | Expedição no cut-off (SC-009) | — | Estoque disponível no feed | Curva de demanda de mão de obra |
| **Middle mile** | — | — | Volume na base até H (MM-007) | — | — |
| **Last mile** | Devoluções ao CD em N dias | — | — | Promessa de prazo por CEP | — |
| **Pessoas** | Reposição e temporários | Motoristas/ajudantes | Onboarding de entregadores | — | — |
| **LSS / EO** | Projetos DMAIC sobre KPIs fora de controle — atende todas as áreas |||||

## Trade-offs que exigem decisão executiva (não do turno)

| Trade-off | KPIs em tensão | Regra recomendada |
|---|---|---|
| Custo × prazo no line-haul | MM-003 × MM-002 | Carreta sai no horário; rota redesenhada se ocupação < X% por N dias |
| Produtividade × qualidade no CD | SC-008 × SC-007 | Meta de produtividade só vale com acurácia ≥ limite |
| Crescimento × lucro na mídia | MK-001 × MK-002 | Orçamento alocado por POAS/incrementalidade, não por ROAS de plataforma |
| Densidade × experiência no last mile | LM-004 × LM-002 | SPH só é reconhecido com FADR e tentativa falsa dentro do limite |
| Velocidade × sustentação no LSS | LS-103 × LS-102 | Projeto só é "fechado" com plano de controle e dono do processo |
