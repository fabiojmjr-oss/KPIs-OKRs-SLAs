"""Gera e executa notebooks/caso_vertice.ipynb (saídas ficam salvas para leitura no GitHub).

Uso: python notebooks/gerar_notebook.py
"""
from pathlib import Path

import nbformat as nbf
from nbconvert.preprocessors import ExecutePreprocessor

AQUI = Path(__file__).resolve().parent
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell

celulas = [
    md("""# Caso Vértice · Da estratégia ao chão do CD, com dados

**Vértice Commerce & Logística** é uma empresa **fictícia** de grande porte, com operação híbrida (própria + 3PL), que em 2025 saiu do Sul/Sudeste para o Brasil inteiro. Este notebook percorre o ciclo completo:

1. **Linha de base × mercado**: onde estamos em relação ao Mercado Livre (divulgação 2T26) e ao WERC 2025
2. **Diagnóstico da cadeia**: como o pico de fim de ano se propaga do CD ao cliente
3. **CEP**: separar ruído de sinal (e o erro da carta p com n gigante)
4. **Capability**: o SLA de dock-to-stock é sustentável?
5. **Capacidade**: equilibrar pessoas, horas extras, temporários e 3PL sem sacrificar custo nem o plano de 2027
6. **OKRs 2026**: nota calculada direto dos dados, com contrapeso

> Dados sintéticos gerados por `kpikit.simulador` (causal, com semente fixa). Benchmarks reais e fontes em `00-fundamentos/linha-de-base-mercado.md`."""),
    code("""import sys; sys.path.insert(0, '..')
import pandas as pd, matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
from kpikit import simulador, kpis, spc, capacidade, okr, config
pd.set_option('display.float_format', '{:,.4f}'.format)
plt.rcParams.update({'figure.dpi': 110, 'axes.spines.top': False, 'axes.spines.right': False})
d = simulador.carregar()
{k: len(v) for k, v in d.items()}"""),
    md("## 1. Linha de base (2º semestre de 2025) × meta 2026 × benchmark"),
    code("""painel = kpis.painel_metas(d)
painel[['kpi_id','kpi','linha_base','meta_2026','benchmark','confianca','fonte_benchmark']]"""),
    md("""**Leitura.** Em 48h, a Vértice (65%) está 12 p.p. atrás da régua pública do Mercado Livre (77% dos envios rápidos em até 48h no 2T26). Os denominadores, porém, não são idênticos: o MELI reporta *envios rápidos*, não o total de pedidos. Na acurácia de picking a distância para o best-in-class do WERC é pequena; no dock-to-stock é grande (7,3 h contra < 3,5 h)."""),
    md("## 2. O pico se propaga pela cadeia"),
    code("""serie = pd.concat([kpis.calcular(d, k, freq='W') for k in ['SC-012','SC-009','MM-002','LM-001']], axis=1)
fig, ax = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
serie['SC-012'].plot(ax=ax[0], color='#7f8c8d', title='Utilização de capacidade dos CDs (semanal)')
ax[0].axhline(1, color='#c0392b', ls='--', lw=1); ax[0].yaxis.set_major_formatter(PercentFormatter(1))
serie[['SC-009','MM-002','LM-001']].plot(ax=ax[1], title='Cut-off (CD) → chegada na janela (middle mile) → OTD (cliente)')
ax[1].yaxis.set_major_formatter(PercentFormatter(1)); ax[1].legend(['Cut-off CD','OTA line-haul','OTD cliente'])
plt.tight_layout()"""),
    code("""bf = ('2025-11-24', '2025-12-01')
pd.DataFrame({k: [kpis.calcular(d, k, inicio='2025-10-01', fim='2025-10-31'), kpis.calcular(d, k, inicio=bf[0], fim=bf[1])]
              for k in ['SC-012','SC-009','SC-007','MM-002','LM-001','LM-002','LM-007']},
             index=['Outubro/25', 'Black Friday/25']).T"""),
    md("""**Leitura.** Quando a utilização dos CDs passa de ~90%, o cut-off cai de forma **não linear**, e cada elo seguinte herda e amplifica a perda: o OTD ao cliente cai mais que o cut-off. Contatos no SAC sobem junto. É o custo invisível do pico mal dimensionado, que volta para o marketing como CAC mais alto."""),
    md("## 3. CEP · ruído ou sinal?"),
    code("""hub = d['fato_hub'].query("unidade_id == 'HUB-BA'").set_index('data').dwell_time_p90_h.dropna()
carta = spc.carta_imr(hub); sinais = spc.regras_nelson(carta)
spc.plotar(carta, 'HUB-BA · Dwell time P90 (h) · carta I', sinais.regra_1)
carta[sinais.regra_1].index.strftime('%d/%m/%Y').tolist()"""),
    md("""A carta I detecta a **pane do sorter (16–18/09/2025)** injetada na simulação e os picos de fim de ano. Nos dias restantes, a variação é ruído comum. Reagir a ela (*tampering*) só aumenta a variação."""),
    code("""cd = d['fato_cd'].query("unidade_id == 'CD-SP1'").set_index('data')
nc = cd.pedidos - cd.pedidos_expedidos_cutoff
fig, ax = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
for a, laney in zip(ax, [False, True]):
    c = spc.carta_p(nc, cd.pedidos, laney=laney); s = spc.regras_nelson(c)
    spc.plotar(c, f"CD-SP1 · % fora do cut-off · {'p′ de Laney' if laney else 'p clássica'} · {s.regra_1.sum()} pontos fora", s.regra_1, ax=a, formato_pct=True)
plt.tight_layout()"""),
    md("""**Erro clássico em logística.** Com ~40 mil pedidos por dia, a carta p clássica tem limites tão estreitos que **quase todos os dias** parecem causa especial. É sobredispersão: a variação real entre dias é muito maior que a binomial. A carta **p′ de Laney** mede essa variação e devolve à carta seu poder de decisão."""),
    md("## 4. Capability · o SLA de dock-to-stock de 12 h é sustentável?"),
    code("""pd.DataFrame({u: spc.capabilidade(d['fato_cd'].query('unidade_id == @u and pedidos > 0').dock_to_stock_p90_h, lse=12)
              for u in sorted(d['fato_cd'].unidade_id.unique())}).T[['media','Cpk','Ppk','pct_fora_spec_observado']]"""),
    md("""Os CDs das regiões em expansão (AM1, GO1, PE1) têm Ppk muito abaixo do Cpk: o processo **ainda não é estável** (curva de aprendizagem + pico). O CD-AM1 não é capaz nem no curto prazo (Cpk < 1). Nesses casos o índice de capability não vale como promessa contratual. A ordem é **controlar, depois medir capability, depois contratar SLA**."""),
    code("""erros, linhas = d['fato_cd'].linhas_com_erro.sum(), d['fato_cd'].linhas_separadas.sum()
dp = spc.dpmo(erros, linhas); print(f'Picking: {dp:,.0f} DPMO → {spc.nivel_sigma(dp):.2f}σ (convenção com deslocamento de 1,5σ)')"""),
    md("""## 5. Capacidade · equilibrar pessoas e recursos sem sacrificar custo nem o futuro

Programação linear semanal para o 4T26 (demanda = 4T25 × 1,35). Decide quadro próprio, contratações, horas extras, temporários e 3PL, minimizando custo com restrições de **SLA** (buffer), **qualidade** (acurácia ponderada do mix), **saúde e legislação** (limite de HE), **risco** (dependência de 3PL) e **futuro** (quadro mínimo ao final)."""),
    code("""cen = capacidade.Cenario(demanda=capacidade.demanda_projetada(d))
r = capacidade.otimizar(cen)
print(f'Custo total R$ {r.custo_total/1e6:,.1f} mi · R$ {r.custo_por_pedido:.2f}/pedido · acurácia do mix {r.acuracia_mix:.3%} · 3PL {r.participacao_3pl:.1%}')
r.plano[['demanda','quadro_proprio','contratacoes','horas_extras','horas_temporarios','pedidos_3pl','acuracia_mix']].round(0)"""),
    code("""ax = r.plano[['ped_proprio','ped_extra','ped_temporario','pedidos_3pl']].plot.bar(stacked=True, figsize=(11, 3.8), width=0.85,
      color=['#3b6ea5','#8fb3d9','#e67e22','#c0392b'], title='Pedidos por fonte de capacidade')
ax.plot(range(len(r.plano)), r.plano.demanda, color='black', marker='o', lw=1.2, label='demanda'); ax.legend(fontsize=8)
r.custo_marginal_pedido.round(2).to_frame().T"""),
    md("""**Leituras para o comitê executivo**

- **O gargalo do pico é o recrutamento, não o orçamento.** Com teto de contratações por semana, o modelo começa a contratar **5 semanas antes** da Black Friday. Isso conecta o KPI de RH (*time-to-fill*, turnover precoce) diretamente ao OTD de dezembro.
- **Preço-sombra.** Na semana da Black Friday, **um pedido a mais custa ~6× o custo médio**. Esse número precisa estar na mesa quando o marketing propõe "mais uma campanha" para aquela semana.
- **Qualidade tem preço, e ele é não linear.** Veja a curva abaixo."""),
    code("""curva = capacidade.curva_tradeoff(cen, 'acuracia_meta', [0.995, 0.996, 0.9964, 0.9966, 0.9968, 0.997])
curva['custo_incremental_mi'] = (curva.custo_total - curva.custo_total.min()) / 1e6
curva[['acuracia_meta','custo_total','custo_incremental_mi','participacao_3pl']]"""),
    md("""Até ~99,64% a meta de acurácia **não custa nada** (a restrição está folgada). A partir daí, cada centésimo de ponto percentual custa milhões, porque força trocar temporário e 3PL por quadro próprio. A decisão certa depende do **custo de um erro** (logística reversa, reenvio, SAC, recompra perdida). Esse número vem de um projeto DMAIC, não de achismo."""),
    code("""pd.concat([capacidade.curva_tradeoff(cen, 'limite_3pl', [0, .1, .2, .3, .4]).set_index('limite_3pl')[['custo_total','participacao_3pl']],
          ], axis=1)"""),
    md("""**Dependência de 3PL (KRI).** Proibir 3PL encarece o pico em ~R$ 24 mi; liberar até 40% economiza pouco. Um teto de 20–30% preserva flexibilidade sem transferir o risco operacional do pico para o parceiro. Na operação híbrida, é um *trade-off* de governança, não só de custo."""),
    md("## 6. OKRs 2026 · nota calculada dos dados (3T26 vs. 2S25)"),
    code("""krs, objs = okr.pontuar(d)
krs[['kr','descricao','tipo','linha_base','meta','atual','nota','status']]"""),
    code("""objs[['objetivo','pilar','nota_media','contrapeso','contrapeso_ok']]"""),
    code("""kpis.calcular(d, 'MM-004', freq='QS', por='regiao_id').unstack().round(2)"""),
    md("""**Leitura de governança.** O O2 (expansão nacional) tem nota alta, mas **violou o contrapeso de custo por kg transferido**. A causa é **efeito mix**, como mostra a quebra por região acima: o Norte custa ~16× o Sudeste por kg, e cada ponto de participação do N/NE sobe a média nacional. Um contrapeso não estratificado penaliza a própria estratégia de expansão. A correção de governança é medir o contrapeso **por região** (ou com mix constante) e decidir no S&OP qual custo é o preço aceito da promessa nacional.

---
*Material de portfólio. Empresa e dados fictícios; referências de mercado citadas com fonte pública.*"""),
]

nb = nbf.v4.new_notebook(cells=celulas, metadata={"kernelspec": {"name": "python3", "display_name": "Python 3",
                                                                 "language": "python"}})
ExecutePreprocessor(timeout=600, kernel_name="python3").preprocess(nb, {"metadata": {"path": str(AQUI)}})
nbf.write(nb, AQUI / "caso_vertice.ipynb")
print("ok:", AQUI / "caso_vertice.ipynb")
