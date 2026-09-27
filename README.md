# KPIs · OKRs · SLAs

Biblioteca de gestão de desempenho que conecta **estratégia → execução → dados**, cobrindo operações logísticas ponta a ponta e as funções que as sustentam.

> Princípio central: **OKR muda o sistema, KPI monitora a saúde do sistema, SLA contrata o nível de serviço entre partes.** Misturar os três é a causa mais comum de painéis com 80 indicadores e nenhuma decisão.

## Estrutura

| Pasta | Conteúdo |
|---|---|
| [`00-fundamentos/`](00-fundamentos/) | Hierarquia OKR/KPI/SLA, governança e cadência (Hoshin Kanri), interdependências entre áreas, anti-padrões |
| [`templates/`](templates/) | Fichas padrão: OKR, KPI (ficha técnica), SLA |
| [`catalogo/kpis.csv`](catalogo/kpis.csv) | Catálogo estruturado de KPIs (base para Power BI / Python / planilha) |
| [`areas/01-supply-chain`](areas/01-supply-chain/) | Planejamento, estoque, armazenagem/CD, SCOR |
| [`areas/02-middle-mile`](areas/02-middle-mile/) | Transferência, line-haul, cross-docking, hubs de triagem |
| [`areas/03-last-mile`](areas/03-last-mile/) | Entrega ao cliente final, first attempt, custo por entrega |
| [`areas/04-gestao-de-pessoas`](areas/04-gestao-de-pessoas/) | Pessoas em operação: turnover, absenteísmo, produtividade, segurança, NR-1 |
| [`areas/05-marketing-trafego`](areas/05-marketing-trafego/) | Mídia paga / tráfego: ROAS, CAC, LTV, incrementalidade |
| [`areas/06-projetos`](areas/06-projetos/) | Gestão de projetos e portfólio: EVM, benefícios, riscos |
| [`areas/07-scrum-agil`](areas/07-scrum-agil/) | Scrum, Kanban, fluxo, EBM, DORA |
| [`areas/08-lean-six-sigma`](areas/08-lean-six-sigma/) | Programa LSS, capability, COPQ, governança de Master Black Belt |

## Como usar

1. Leia [`00-fundamentos/hierarquia-okr-kpi-sla.md`](00-fundamentos/hierarquia-okr-kpi-sla.md) — define a gramática comum.
2. Escolha a área, parta da **árvore de KPIs** (North Star → drivers → operacionais).
3. Selecione 3–5 KPIs de saúde, escreva no máximo 3 Objetivos com 3–4 KRs e formalize os SLAs de interface.
4. Documente cada KPI com a [ficha técnica](templates/kpi-ficha.md) antes de colocá-lo em painel.
5. Rode a cadência de [`00-fundamentos/governanca-e-cadencia.md`](00-fundamentos/governanca-e-cadencia.md).

## Convenções

- **Metas e benchmarks** marcados com ⚠️ são referências indicativas: validar contra a edição vigente da fonte e contra a linha de base própria antes de contratar.
- Toda métrica tem **polaridade** (↑ maior é melhor / ↓ menor é melhor), **tipo** (leading/lagging) e **dono**.
- Todo KPI de eficiência é pareado com um KPI de qualidade/serviço (*métrica de contrapeso*) para neutralizar a Lei de Goodhart.
