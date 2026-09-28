# Linha de base de mercado (referência: set/2026)

Mercado Livre e Amazon são a régua de mercado em velocidade e confiabilidade de entrega — mas **divulgam poucos KPIs operacionais**. Eles publicam resultados de negócio e de velocidade; não publicam acurácia de picking, FADR, dwell time ou custo por entrega. Por isso, a linha de base deste repositório é construída em camadas, cada uma com seu **nível de confiança**:

| Nível | Origem | Como usar |
|---|---|---|
| **A** | Divulgação oficial da empresa (release trimestral, carta a acionistas, press release) | Meta estratégica / North Star |
| **B** | Pesquisa de associação setorial com metodologia publicada (ex.: WERC) | Meta operacional de referência |
| **C** | Fornecedores de software, blogs setoriais, consultorias sem metodologia aberta | Ordem de grandeza — nunca meta contratual |
| **D** | Premissa do caso (inferência explícita) | Declarada como premissa; substituir por dado real |

## Camada A — Divulgações oficiais

| Player | Métrica divulgada | Valor | Período | Fonte |
|---|---|---|---|---|
| Mercado Livre | Envios rápidos entregues em até 48h | **77%** | 2T26 | Release de resultados 2T26 (ago/2026) |
| Mercado Livre | Envios same/next day | **225 milhões** (+38% a/a) | 2T26 | Release 2T26 |
| Mercado Livre | Receita líquida | US$ 10 bi (+50% a/a) · margem operacional 6,7% | 2T26 | Release 2T26 |
| Mercado Livre | Brasil: itens vendidos / GMV FX-neutro | +56% / +39% a/a | 2T26 | Release 2T26 |
| Mercado Livre | Brasil: conversão | +1,1 p.p. a/a | 2T26 | Teleconferência 2T26 |
| Mercado Livre | Frete grátis no Brasil | Limite reduzido para R$ 19 (meados de 2025) | 2025 | Comunicação da empresa / imprensa |
| Mercado Livre | Rede de fulfillment Brasil | Plano de 14 novos CDs em 2026 → 42 no total | 2026 | Teleconferência / imprensa ⚠️ |
| Amazon | Itens same/next day entregues a membros Prime (global) | **> 13 bilhões** (+44% vs 2024) | 2025 | Press release Amazon, fev/2026 |
| Amazon | Idem, EUA | > 8 bilhões (+30% a/a) | 2025 | Press release Amazon, fev/2026 |
| Amazon | Rede rural EUA | US$ 4 bi de investimento; same/next day em > 4.000 cidades pequenas | 2025 | Press release Amazon, fev/2026 |

**Leitura executiva**
1. **A disputa é por velocidade como padrão, não como premium.** Os dois players reportam volume same/next day como indicador de negócio junto com receita. Velocidade virou KPI de board.
2. **Velocidade vem com custo e pressão de margem.** O Mercado Livre aceitou margem operacional de 6,7% para investir em frete e em rede. O trade-off receita × margem × rede (ver [interdependências](interdependencias.md)) é real e está nos números.
3. **Escala derruba custo unitário.** A empresa relatou queda do custo de entrega por unidade no Brasil com o aumento de volume. É a curva que justifica expansão nacional com densidade.

## Camada B — Benchmarks operacionais (WERC DC Measures 2025)

| KPI | Best-in-class | ID no catálogo |
|---|---|---|
| Expedições no prazo | ≥ 99,5% | SC-009 |
| Acurácia de picking (% por pedido) | ≥ 99,68% | SC-007 |
| Dock-to-stock | < 3,5 h | SC-006 |

Fonte: WERC, *DC Measures 2025* (divulgado em set/2025), pesquisas de 2024–2025 com respondentes de manufatura, varejo, atacado, 3PL e life sciences. O relatório completo é pago; os valores acima são os divulgados publicamente pela WERC e pela imprensa especializada.

## Camada C — Ordens de grandeza (last mile)

| KPI | Faixa observada | Observação |
|---|---|---|
| FADR (sucesso na 1ª tentativa) | 80–92%; "forte" > 90% | Fontes de fornecedores de roteirização; endereço incorreto aparece como principal causa de falha |
| Participação do last mile no custo da cadeia | ~41% | Capgemini Research Institute, 2019 — estimativa antiga |

## Camada D — Premissas do caso integrado
As metas do caso fictício ([`caso-integrado/`](../caso-integrado/)) combinam A + B + C com premissas declaradas no código (`kpikit/config.py`). Exemplo: "D+1/D+2 em 80% dos pedidos até dez/2026" parte do 77% em 48h do Mercado Livre (A) e é ajustada para uma empresa em expansão.

## Regras de uso
- Revisar esta página a **cada release trimestral** (MELI: mai/ago/nov/fev; Amazon: carta anual em abril e press release de entregas em fevereiro).
- **Não comparar definições diferentes**: "77% em até 48h" do MELI refere-se a *envios rápidos*, não ao total de pedidos. Documente o denominador.
- Material de portfólio público: citar sempre a fonte, e nunca sugerir afiliação com as empresas nem usar dados não públicos.

## Fontes
- Mercado Libre — Q2 2026 Results (Business Wire / Investor Relations, ago/2026): https://investor.mercadolibre.com
- Mercado Libre Q2 2026 earnings call (resumos Yahoo Finance / Investing.com, ago/2026)
- Amazon — "Amazon Sets New Prime Delivery Speed Record in 2025…" (Business Wire, 03/02/2026): https://www.aboutamazon.com/news/retail/amazon-prime-same-day-next-day-delivery-2025
- WERC — 2025 DC Measures Report: https://werc.org/news/702949/
- Capgemini Research Institute — *The last-mile delivery challenge* (2019)
