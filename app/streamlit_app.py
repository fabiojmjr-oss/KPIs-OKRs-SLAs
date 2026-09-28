"""Painel de desempenho — caso Vértice (empresa fictícia).

Executar:  streamlit run app/streamlit_app.py
"""
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from kpikit import capacidade, config, dmaic, kpis, okr, pessoas, simulador, spc  # noqa: E402

st.set_page_config(page_title="Vértice · KPIs, OKRs e SLAs", layout="wide")

AZUL, VERMELHO, CINZA, VERDE = "#3b6ea5", "#c0392b", "#7f8c8d", "#2e8b57"
FREQS = {"Diário": "D", "Semanal": "W", "Mensal": "MS", "Trimestral": "QS"}
PERIODO_ATUAL = ("2026-07-01", "2026-09-30")


@st.cache_data
def dados():
    return simulador.carregar()


@st.cache_data
def okrs_pontuados():
    return okr.pontuar(dados())


@st.cache_data
def absenteismo_previsto():
    return pessoas.previsao_absenteismo(dados())


@st.cache_data
def modelo_saida():
    X, y = pessoas.matriz_risco_saida(dados()["fato_colaboradores"], config.FIM)
    return pessoas.regressao_logistica(X, y)


def e_percentual(kpi_id: str) -> bool:
    return "%" in kpis.REGISTRO[kpi_id].formato


d = dados()
st.title("Vértice · Painel de Desempenho")
st.caption(f"{config.EMPRESA} · dados sintéticos de {config.INICIO:%d/%m/%Y} a {config.FIM:%d/%m/%Y} · "
           "benchmarks reais em 00-fundamentos/linha-de-base-mercado.md")

abas = st.tabs(["Executivo", "OKRs 2026", "Operação", "CEP", "Capacidade", "Pessoas", "DMAIC", "Marketing"])

# ---------------------------------------------------------------- Executivo
with abas[0]:
    st.subheader("KPIs estratégicos · 3T26 vs. linha de base (2S25), meta 2026 e benchmark")
    painel = kpis.painel_metas(d)
    cols = st.columns(3)
    for i, lin in painel.iterrows():
        atual = float(kpis.calcular(d, lin.kpi_id, inicio=PERIODO_ATUAL[0], fim=PERIODO_ATUAL[1]))
        melhora = (atual - lin.linha_base) * (1 if lin.polaridade == "maior" else -1)
        with cols[i % 3]:
            st.metric(f"{lin.kpi} ({lin.kpi_id})", kpis.formatar(lin.kpi_id, atual),
                      delta=("▲ " if melhora >= 0 else "▼ ") + "vs. base " + kpis.formatar(lin.kpi_id, lin.linha_base),
                      delta_color="normal" if melhora >= 0 else "inverse")
            bench = "—" if pd.isna(lin.benchmark) else f"{kpis.formatar(lin.kpi_id, lin.benchmark)} [{lin.confianca}]"
            st.caption(f"Meta: **{kpis.formatar(lin.kpi_id, lin.meta_2026)}** · Benchmark: {bench}")
    st.divider()
    st.markdown("**Leitura de rede · entregas em até 48h por região (mensal)**")
    s = kpis.calcular(d, "LM-011", freq="MS", por="regiao_id").reset_index()
    fig = px.line(s, x="data", y="LM-011", color="regiao_id", markers=True)
    fig.add_hline(y=0.77, line_dash="dot", line_color=CINZA,
                  annotation_text="Mercado Livre 2T26: 77% dos envios rápidos em até 48h")
    fig.update_layout(yaxis_tickformat=".0%", height=380, legend_title="Região", xaxis_title="")
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------- OKRs
with abas[1]:
    krs, objs = okrs_pontuados()
    st.subheader("OKRs 2026 · nota em 3T26 (0–1)")
    st.caption("Committed espera 1,0; aspirational com 0,7 já é sucesso. Contrapeso violado invalida a comemoração.")
    for _, o in objs.iterrows():
        cp = "✅" if o.contrapeso_ok else "⚠️ contrapeso violado"
        st.markdown(f"#### {o.objetivo} · {o.descricao}  \n*{o.pilar}* · {o.dono} · "
                    f"nota média **{o.nota_media:.2f}** · {o.contrapeso} {cp}")
        t = krs[krs.objetivo == o.objetivo].copy()
        for c in ("linha_base", "meta", "atual"):
            t[c] = [kpis.formatar(k, v) if k in kpis.REGISTRO else f"{v:.3f}" for k, v in zip(t.kpi_id, t[c])]
        st.dataframe(t[["kr", "descricao", "tipo", "linha_base", "meta", "atual", "nota", "status"]],
                     hide_index=True, use_container_width=True,
                     column_config={"nota": st.column_config.ProgressColumn("nota", min_value=0, max_value=1,
                                                                            format="%.2f")})

# ---------------------------------------------------------------- Operação
with abas[2]:
    c1, c2, c3 = st.columns([2, 1, 1])
    opcoes = {f"{k} · {v.nome}": k for k, v in kpis.REGISTRO.items() if v.tabela != "fato_midia"}
    kpi_id = opcoes[c1.selectbox("KPI", list(opcoes), index=list(opcoes.values()).index("LM-001"))]
    freq = FREQS[c2.selectbox("Granularidade", list(FREQS), index=1)]
    corte = c3.selectbox("Abrir por", ["(total)", "regiao_id", "unidade_id"])
    s = kpis.calcular(d, kpi_id, freq=freq, por=None if corte == "(total)" else corte).reset_index()
    fig = px.line(s, x="data", y=kpi_id, color=None if corte == "(total)" else corte)
    meta = next((m for m in config.METAS_2026 if m.kpi_id == kpi_id), None)
    if meta:
        fig.add_hline(y=meta.meta, line_dash="dash", line_color=VERDE, annotation_text="meta 2026")
    for _, nome, ini in [(k, *v) for k, v in config.INICIATIVAS.items()]:
        fig.add_vline(x=pd.Timestamp(ini).timestamp() * 1000, line_width=0.5, line_color=CINZA)
    fig.update_layout(height=420, xaxis_title="", yaxis_tickformat=".1%" if e_percentual(kpi_id) else None)
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Linhas verticais: início das iniciativas 2026. "
               + " · ".join(f"{v[1]:%d/%m} {v[0]}" for v in config.INICIATIVAS.values()))

# ---------------------------------------------------------------- CEP
with abas[3]:
    st.subheader("Controle Estatístico de Processo")
    modo = st.radio("Carta", ["Dwell time do hub (I-MR)", "Não conformes no cut-off do CD (p / p′ Laney)",
                              "Dock-to-stock do CD (I-MR + capability)"], horizontal=True)
    if modo.startswith("Dwell"):
        hub = st.selectbox("Hub", sorted(d["fato_hub"].unidade_id.unique()), index=0)
        x = d["fato_hub"].query("unidade_id == @hub").set_index("data").dwell_time_p90_h.dropna()
        carta = spc.carta_imr(x)
    else:
        cd = st.selectbox("CD", sorted(d["fato_cd"].unidade_id.unique()), index=4)
        df = d["fato_cd"].query("unidade_id == @cd and pedidos > 0").set_index("data")
        if modo.startswith("Não"):
            laney = st.toggle("Usar p′ de Laney (corrige sobredispersão)", value=True)
            carta = spc.carta_p(df.pedidos - df.pedidos_expedidos_cutoff, df.pedidos, laney=laney)
        else:
            carta = spc.carta_imr(df.dock_to_stock_p90_h)
    sinais = spc.regras_nelson(carta)
    fig = go.Figure()
    fig.add_scatter(x=carta.index, y=carta.valor, mode="lines+markers", marker_size=3, line_color=AZUL, name="valor")
    for col, cor, dash in [("centro", CINZA, None), ("lsc", VERMELHO, "dash"), ("lic", VERMELHO, "dash")]:
        fig.add_scatter(x=carta.index, y=carta[col], mode="lines", line=dict(color=cor, dash=dash, width=1), name=col)
    pts = carta[sinais.algum_sinal]
    fig.add_scatter(x=pts.index, y=pts.valor, mode="markers", marker=dict(color=VERMELHO, size=7), name="sinal")
    fig.update_layout(height=420)
    st.plotly_chart(fig, use_container_width=True)
    st.write(sinais.drop(columns="algum_sinal").sum().rename("pontos sinalizados").to_frame().T)
    if modo.startswith("Dock"):
        lse = st.number_input("LSE — SLA de dock-to-stock (h)", value=12.0, step=1.0)
        cap = spc.capabilidade(df.dock_to_stock_p90_h, lse=lse)
        c = st.columns(4)
        c[0].metric("Cpk (curto prazo)", f"{cap['Cpk']:.2f}")
        c[1].metric("Ppk (longo prazo)", f"{cap['Ppk']:.2f}")
        c[2].metric("% dias fora do SLA", f"{cap['pct_fora_spec_observado']:.1%}")
        c[3].metric("Média", f"{cap['media']:.1f} h")
        st.caption("Ppk muito abaixo de Cpk indica processo instável: capability só vale depois do controle.")

# ---------------------------------------------------------------- Capacidade
with abas[4]:
    st.subheader("Mix de recursos para o pico (programação linear)")
    st.caption("Pessoas próprias, horas extras, temporários e 3PL, com o menor custo que respeite SLA, qualidade, "
               "limites legais/saúde, dependência de terceiros e o quadro necessário para os planos de 2027.")
    c = st.columns(4)
    cres = c[0].slider("Crescimento sobre 2025", 0.0, 0.8, 0.35, 0.05)
    acc = c[1].slider("Meta de acurácia do mix", 0.9950, 0.9972, 0.9968, 0.0001, format="%.4f")
    l3 = c[2].slider("Limite 3PL (% demanda)", 0.0, 0.6, 0.30, 0.05)
    lt = c[3].slider("Limite temporários (% horas)", 0.0, 0.5, 0.25, 0.05)
    c = st.columns(4)
    lhe = c[0].slider("Limite hora extra (% horas)", 0.0, 0.3, 0.15, 0.01)
    contr = c[1].slider("Contratações máx./semana", 100, 1500, 500, 50)
    hcf = c[2].number_input("Quadro próprio mínimo ao final (0 = sem)", 0, 20_000, 0, 250)
    orc = c[3].number_input("Orçamento do período (R$ mi, 0 = sem)", 0.0, 1_000.0, 0.0, 5.0)
    cen = capacidade.Cenario(demanda=capacidade.demanda_projetada(d, crescimento=cres), acuracia_meta=acc,
                             limite_3pl=l3, limite_temp=lt, limite_he=lhe, max_contratacoes_semana=contr,
                             hc_final_minimo=hcf or None, orcamento=orc * 1e6 or None)
    r = capacidade.otimizar(cen)
    if r.status != "otimo":
        st.error("Sem solução viável com essas políticas. Relaxe uma restrição: é exatamente a conversa "
                 "de trade-off que precisa acontecer no S&OP, não no chão do CD.")
    else:
        k = st.columns(4)
        k[0].metric("Custo total", f"R$ {r.custo_total / 1e6:,.1f} mi")
        k[1].metric("Custo por pedido", f"R$ {r.custo_por_pedido:.2f}")
        k[2].metric("Acurácia do mix", f"{r.acuracia_mix:.3%}")
        k[3].metric("Participação 3PL", f"{r.participacao_3pl:.1%}")
        p = r.plano.reset_index()
        fontes = p.melt(id_vars="semana", value_vars=["ped_proprio", "ped_extra", "ped_temporario", "pedidos_3pl"],
                        var_name="fonte", value_name="pedidos")
        fig = px.bar(fontes, x="semana", y="pedidos", color="fonte", title="Pedidos por fonte de capacidade")
        fig.add_scatter(x=p.semana, y=p.demanda, mode="lines+markers", name="demanda", line_color="black")
        st.plotly_chart(fig, use_container_width=True)
        c1, c2 = st.columns(2)
        f2 = px.bar(r.custo_marginal_pedido.reset_index(), x="semana", y="custo_marginal_pedido",
                    title="Custo marginal de 1 pedido a mais (preço-sombra, R$)")
        c1.plotly_chart(f2, use_container_width=True)
        f3 = px.line(p, x="semana", y="quadro_proprio", markers=True, title="Quadro próprio (operadores)")
        c2.plotly_chart(f3, use_container_width=True)
        with st.expander("Curva de trade-off: custo × meta de acurácia"):
            curva = capacidade.curva_tradeoff(cen, "acuracia_meta", [0.9955, 0.996, 0.9964, 0.9966, 0.9968, 0.997])
            st.dataframe(curva, hide_index=True)
        with st.expander("Plano semanal"):
            st.dataframe(r.plano, use_container_width=True)

# ---------------------------------------------------------------- Pessoas
with abas[5]:
    st.subheader("Força de trabalho · retenção e escala")
    base_sv = pessoas.base_sobrevivencia(d["fato_colaboradores"], config.FIM)
    fator = st.selectbox("Curva de retenção por", ["com_buddy", "canal_recrutamento", "turno", "modelo", "regiao_id"])
    fig = go.Figure()
    for valor, g in base_sv.groupby(fator):
        k = pessoas.kaplan_meier(g.dias, g.evento)
        k = k[k.index <= 180]
        fig.add_scatter(x=k.index, y=k.sobrevivencia, mode="lines", line_shape="hv", name=f"{valor} (n={len(g):,})")
    fig.add_vline(x=90, line_dash="dot", line_color=CINZA)
    fig.update_layout(height=380, yaxis_tickformat=".0%", xaxis_title="dias desde a admissão",
                      yaxis_title="ainda na empresa", yaxis_range=[0.4, 1.01])
    st.plotly_chart(fig, use_container_width=True)
    lr = pessoas.logrank(base_sv.dias.clip(upper=90), base_sv.evento.where(base_sv.dias <= 90, 0), base_sv[fator])
    st.caption(f"Log-rank até 90 dias: χ² = {lr['qui2']:.1f}, p = {lr['p_valor']:.1e}. Kaplan-Meier trata quem ainda "
               "está ativo como censurado (sem viés de coorte imatura).")
    with st.expander("Fatores de risco de saída em 90 dias (regressão logística)"):
        st.dataframe(modelo_saida()[["razao_chances", "rc_ic_inf", "rc_ic_sup", "p_valor"]].round(3),
                     use_container_width=True)
    st.divider()
    st.markdown("**Escala 6x1 · programação inteira**")
    prev, _ = absenteismo_previsto()
    c = st.columns(3)
    cd_esc = c[0].selectbox("CD", sorted(d["fato_cd"].unidade_id.unique()), index=5, key="cd_escala")
    pct = c[1].slider("Percentil da demanda para dimensionar", 0.5, 0.95, 0.85, 0.05)
    dom = c[2].slider("Mínimo do quadro com folga no domingo", 0.0, 0.5, 0.0, 0.05)
    nec = pessoas.necessidade_semanal(d, cd_esc, "2026-04-01", "2026-09-30", percentil=pct)
    ab = (prev.query("unidade_id == @cd_esc and amostra == 'teste'")
          .assign(dia=lambda x: x.data.dt.dayofweek.map(dict(enumerate(pessoas.DIAS))))
          .groupby("dia").previsto.mean().reindex(pessoas.DIAS))
    esc = pessoas.escala_6x1(nec, ab, folga_domingo_min=dom)
    k = st.columns(3)
    k[0].metric("Quadro otimizado", f"{esc.quadro:,}")
    k[1].metric("Quadro plano (pior dia)", f"{esc.quadro_ingenuo:,}", delta=f"{esc.quadro - esc.quadro_ingenuo:,}",
                delta_color="inverse")
    k[2].metric("Ociosidade da escala (PE-012)", f"{esc.horas_ociosas_pct:.1%}")
    cob = esc.cobertura.reset_index()
    fig = px.bar(cob, x="dia", y=["presentes_esperados"], title="Presentes esperados × necessidade")
    fig.add_scatter(x=cob.dia, y=cob.necessidade, mode="lines+markers", name="necessidade", line_color="black")
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------- DMAIC
with abas[6]:
    st.subheader("DMAIC · dock-to-stock do CD-AM1")
    rec = d["fato_recebimentos_am1"]
    cap_f = pd.DataFrame({f: dmaic.capabilidade_nao_normal(rec.loc[rec.fase == f, "dock_to_stock_h"])
                          for f in dmaic.JANELAS}).T
    k = st.columns(3)
    for col, f in zip(k, dmaic.JANELAS):
        col.metric(f"P90 · {f}", f"{cap_f.loc[f, 'p90']:.1f} h", help=f"Ppk (percentis) {cap_f.loc[f, 'ppk_percentil']:.2f}")
    c1, c2 = st.columns(2)
    base_m = rec[rec.fase == "medir"]
    par = pd.concat({"todas as cargas": dmaic.pareto(base_m).pct,
                     "acima do SLA": dmaic.pareto(base_m, so_cauda=True).pct}, axis=1).reset_index(names="etapa")
    c1.plotly_chart(px.bar(par, x="etapa", y=["todas as cargas", "acima do SLA"], barmode="group",
                           title="Pareto: a média e a cauda têm causas diferentes").update_layout(yaxis_tickformat=".0%"),
                    use_container_width=True)
    serie = dmaic.serie_diaria_p90(rec).reset_index(names="dia")
    fig = px.line(serie, x="dia", y="p90", color="fase", markers=True, title="P90 diário por fase")
    fig.add_hline(y=dmaic.LSE_HORAS, line_dash="dash", line_color=VERMELHO, annotation_text="SLA 12 h")
    c2.plotly_chart(fig, use_container_width=True)
    st.dataframe(cap_f[["n", "mediana", "p90", "pct_fora_sla", "ppk_percentil", "ppk_normal_enganoso"]].round(3),
                 use_container_width=True)
    st.caption("Ppk pelo método dos percentis (ISO 22514-2). O Ppk 'normal' superestima a capacidade em tempos com cauda "
               "longa. Análise completa em notebooks/dmaic_dock_to_stock_am1.ipynb.")

# ---------------------------------------------------------------- Marketing
with abas[7]:
    st.subheader("Mídia paga · ROAS de plataforma × POAS × MER")
    m = pd.concat([kpis.calcular(d, "MK-001", freq="MS"), kpis.calcular(d, "MK-002", freq="MS"),
                   kpis.mer(d, freq="MS").rename("MER")], axis=1).reset_index()
    fig = px.line(m, x="data", y=["MK-001", "MK-002", "MER"], markers=True)
    fig.update_layout(height=380, yaxis_title="x investimento", xaxis_title="")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("A soma das conversões atribuídas pelas plataformas excede as vendas reais: o ROAS de plataforma "
               "serve para otimização tática; a alocação de orçamento usa POAS, MER e testes de incrementalidade.")
    por_canal = pd.concat([kpis.calcular(d, k, por="canal", inicio=PERIODO_ATUAL[0]) for k in
                           ("MK-001", "MK-002", "MK-004", "MK-007")], axis=1)
    st.dataframe(por_canal.style.format({"MK-001": "{:.2f}x", "MK-002": "{:.2f}x", "MK-004": "R$ {:.2f}",
                                         "MK-007": "{:.2%}"}), use_container_width=True)
