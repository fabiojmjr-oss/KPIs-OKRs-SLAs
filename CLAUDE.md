# Convenções do repositório

- Idioma: português (Brasil), registro executivo.
- Cada área em `areas/NN-nome/README.md` segue a ordem: mental model → árvore de KPIs → tabela de KPIs → OKRs de exemplo → SLAs → caso de mercado.
- IDs de KPI: prefixo da área + número (`SC`, `MM`, `LM`, `PE`, `MK`, `PJ`, `AG`, `LS`). Todo KPI citado em tabela ou em `kpikit.kpis.REGISTRO` deve existir em `catalogo/kpis.csv` com o mesmo ID.
- Benchmarks: nível de confiança A/B/C/D (ver `00-fundamentos/linha-de-base-mercado.md`); ⚠️ quando não verificado. Nunca inventar números de mercado.
- Caso Vértice: empresa e dados fictícios. Premissas ficam em `kpikit/config.py`; linha de base é calculada dos dados, nunca digitada.
- Números citados em textos (README, notebook, caso) devem ser conferidos contra a saída do código.
- Ambiente: `python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt`.
- Notebooks são gerados por código: células em `notebooks/nb_*.py`, executados por `notebooks/gerar_notebook.py`. Edite o `.py`, nunca o `.ipynb`. Didática fica nos notebooks (caixas 🧠/🎯); o código de `kpikit/` fica limpo.
- Após mudanças: `ruff check .`, `ruff format kpikit app tests catalogo`, `python catalogo/validar_catalogo.py`, `python catalogo/verificar_docs.py`, `pytest -q`, `python -m kpikit.simulador` e, se o simulador mudar, `python notebooks/gerar_notebook.py`.
