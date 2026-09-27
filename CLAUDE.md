# Convenções do repositório

- Idioma: português (Brasil), registro executivo.
- Cada área em `areas/NN-nome/README.md` segue a ordem: mental model → árvore de KPIs → tabela de KPIs → OKRs de exemplo → SLAs → caso de mercado.
- IDs de KPI: prefixo da área + número (`SC`, `MM`, `LM`, `PE`, `MK`, `PJ`, `AG`, `LS`). Todo KPI citado em tabela deve existir em `catalogo/kpis.csv` com o mesmo ID.
- Benchmarks sem fonte verificada recebem ⚠️. Nunca inventar números de mercado.
- Após editar o catálogo, rodar `python3 catalogo/validar_catalogo.py`.
