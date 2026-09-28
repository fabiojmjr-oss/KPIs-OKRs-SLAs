"""Notebook: middle mile — consolidação, política de despacho e roteirização milk run (didático)."""
from _celulas import code, md

CELULAS = [
    md("""# Middle mile · encher o caminhão, sair no horário, escolher o caminho

No caso Vértice, o objetivo O2 (expansão nacional) atingiu a pontualidade do line-haul, mas **estourou o contrapeso de custo por kg**. Este notebook abre a caixa do middle mile e ataca as três decisões que formam esse custo:

| # | Decisão | Técnica | KPI |
|---|---|---|---|
| 1 | Como encher o veículo? | Bin packing 2D (heurística FFD × ótimo por programação inteira) · mix de frota | MM-003 |
| 2 | Esperar encher ou sair no horário? | Simulação de eventos discretos (hora a hora, 60 dias) | MM-002, MM-012 |
| 3 | Em que ordem visitar as cidades? | Clarke-Wright + 2-opt · dimensionamento do veículo por rota | MM-004, MM-011, MM-013 |
| 4 | Vale abrir um ponto de transbordo? Onde? | Localização de instalações por enumeração + roteirização por satélite | MM-004, MM-012, LM-011 |

> Caixas **🧠 Por dentro** explicam técnica e código; **🎯 Leitura executiva** traduz em decisão. Especificações de veículos, custos e demanda são premissas (camada D); coordenadas das cidades são aproximadas."""),
    code("""import sys; sys.path.insert(0, '..')
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from kpikit import middle_mile as mm
pd.set_option('display.float_format', '{:,.3f}'.format)
plt.rcParams.update({'figure.dpi': 110, 'axes.spines.top': False, 'axes.spines.right': False})
pd.DataFrame([vars(v) for v in mm.FROTA.values()]).set_index('nome')"""),

    md("## 1. Consolidação · o que enche o caminhão: kg ou m³?"),
    code("""lotes = mm.gerar_lotes(120)
truck = mm.FROTA['Truck']
alocado = mm.consolidar(lotes, truck)
ocup = mm.resumo_ocupacao(alocado, truck)
print(f"{len(lotes)} lotes · {lotes.peso_kg.sum():,.0f} kg · {lotes.volume_m3.sum():,.1f} m³ · densidade média {lotes.peso_kg.sum()/lotes.volume_m3.sum():,.0f} kg/m³")
print(f"Veículos (FFD): {len(ocup)} · limite inferior teórico: {mm.limite_inferior_veiculos(lotes, truck)}")
ocup"""),
    md("""🧠 **Por dentro da técnica · bin packing em 2 dimensões.** Cada lote tem peso **e** volume, e o veículo tem limite nos dois. A heurística **First-Fit Decreasing (FFD)** ordena os lotes do "mais difícil" para o mais fácil (pela dimensão dominante: `max(peso/cap_peso, volume/cap_volume)`) e coloca cada um no primeiro veículo em que cabe. É rápida e costuma ficar a 1 veículo do ótimo.

O **limite inferior** (`ceil(max(Σpeso/cap, Σvolume/cap))`) é a régua: nenhuma solução usa menos veículos que isso. Quando FFD = limite inferior, a solução é comprovadamente ótima.

🎯 **Leitura executiva.** Com carga de e-commerce (~150 kg/m³), **o volume enche o veículo antes do peso**: ocupação de ~85% em m³ contra ~55% em kg. Um painel que mede ocupação só por peso mostra ociosidade que não existe e empurra a decisão errada (consolidar mais em um veículo que já está cheio). Por isso o KPI MM-003 é definido na **restrição ativa**."""),
    code("""pequeno = mm.gerar_lotes(25, semente=5)
vuc = mm.FROTA['VUC']
n_otimo, _ = mm.consolidar_otimo(pequeno, vuc)
print(f"VUC · 25 lotes → limite inferior {mm.limite_inferior_veiculos(pequeno, vuc)} · FFD {mm.consolidar(pequeno, vuc).veiculo.nunique()} · ótimo (MILP) {n_otimo}")"""),
    md("""🧠 **Heurística × ótimo.** `consolidar_otimo` resolve o mesmo problema de forma exata, por programação inteira (`scipy.optimize.milp`): variável binária *x[i,b]* = "lote *i* vai no veículo *b*". O custo computacional explode com o tamanho, e é por isso que operações reais usam heurísticas e guardam o exato para validá-las em amostras. A **quebra de simetria** (usar o veículo 2 só se o 1 estiver em uso) corta soluções equivalentes e acelera o solver."""),
    code("""cargas = {'4 t · 26 m³': (4_000, 26), '7 t · 40 m³': (7_000, 40), '20 t · 100 m³': (20_000, 100), '30 t · 170 m³': (30_000, 170)}
pd.concat({k: mm.mix_frota(kg_, m3_, km_ida_volta=240) for k, (kg_, m3_) in cargas.items()}, names=['carga do dia'])"""),
    md("""🎯 **Mix de frota.** A combinação de menor custo muda com o **perfil da carga**, e nem sempre é "o maior veículo que couber". Para 20 t e 100 m³, o ótimo é **carreta + VUC**, não duas carretas: o excedente de 10 m³ não justifica uma segunda carreta. Com as premissas de custo usadas aqui, a escolha praticamente não muda com a distância. Com custo fixo mais alto ou pedágio por eixo, passaria a mudar, e por isso o modelo recebe a distância. É um problema inteiro pequeno que o planejador deveria rodar por rota, não uma tabela fixa."""),

    md("## 2. Política de despacho · esperar encher ou sair no horário?"),
    code("""carreta = mm.FROTA['Carreta']
curva = mm.curva_despacho(volume_dia_m3=350, veiculo=carreta, km_ida_volta=240, prazo_h=8)
curva"""),
    code("""fig, ax = plt.subplots(figsize=(9, 4.2))
cores = {'encher': '#2e8b57', 'encher_sem_trava': '#c0392b', 'horario': '#3b6ea5'}
rotulos = {'encher': 'encher até X% (com trava de 4 h)', 'encher_sem_trava': 'encher até X% (sem trava)', 'horario': 'sair a cada N horas'}
for pol, g in curva.sort_values('custo_por_m3').groupby('politica'):
    ax.plot(g.custo_por_m3, g.pct_volume_no_prazo, marker='o', color=cores[pol], label=rotulos[pol])
    for _, r in g.iterrows():
        ax.annotate(f"{r.parametro:g}", (r.custo_por_m3, r.pct_volume_no_prazo), fontsize=7, xytext=(3, 3), textcoords='offset points')
ax.set_xlabel('custo por m³ (R$)'); ax.set_ylabel('volume que sai do hub no prazo (8 h)')
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{v:.0%}')); ax.legend(frameon=False, fontsize=8)
ax.set_title('Fronteira custo × pontualidade · faixa de 350 m³/dia, carreta', loc='left')"""),
    md("""🧠 **Por dentro da técnica · simulação de eventos discretos.** O hub recebe volume hora a hora (Poisson, com o perfil do dia: pico no fim da tarde). A cada hora, a política decide se o veículo sai. O embarque é **FIFO**: o volume mais antigo embarca primeiro, e cada m³ carrega a hora em que chegou. Isso permite medir exatamente quanto saiu dentro do prazo. Rodamos 60 dias para a média não depender de um dia atípico. É a técnica certa quando não existe fórmula fechada e o que importa é a interação entre **aleatoriedade** e **regra de decisão**.

🎯 **Leitura executiva**
- **Sair em horário fixo curto** (a cada 2–4 h) garante o prazo, mas roda com o veículo meio vazio: é a política cara.
- **Esperar encher sem trava** é a mais barata, mas **perde prazo** justamente nas horas de pouco volume (madrugada). É a política que um gestor pressionado por custo adota sem perceber o efeito no cliente.
- **A regra híbrida** ("sai quando atingir 80% **ou** quando o volume mais antigo esperar metade do prazo") fica na fronteira: **100% no prazo** com custo por m³ **~12% menor** que sair a cada 4 h (R$ 34 × R$ 38,6). Para descer abaixo disso, até ~R$ 25/m³, é preciso **aceitar 3–6% do volume fora do prazo**. É uma decisão explícita de nível de serviço, que deve estar **escrita no procedimento** e não ser decidida no turno. É exatamente o trade-off ocupação × pontualidade (MM-003 × MM-002) de `00-fundamentos/interdependencias.md`."""),

    md("## 3. Roteirização · milk run a partir do hub de Recife"),
    code("""C = mm.CIDADES_NE
D = mm.matriz_distancias(C)
kg = C.demanda_kg.to_numpy(float); m3 = kg / mm.DENSIDADE_ECOMMERCE_KG_M3
nomes = C.cidade.tolist()
print(f"{len(C)-1} cidades · {kg.sum():,.0f} kg/dia · {m3.sum():,.0f} m³/dia · Recife→Natal ≈ {D[0, nomes.index('Natal')]:.0f} km · Recife→Sousa ≈ {D[0, nomes.index('Sousa')]:.0f} km")"""),
    md("""🧠 **Por dentro da técnica · Clarke-Wright (1964).** Comece com uma rota exclusiva por cidade (hub → cidade → hub). Unir as rotas de *i* e *j* economiza

$$s(i,j) = d(0,i) + d(0,j) - d(i,j)$$

porque o veículo deixa de voltar ao hub entre *i* e *j*. O algoritmo ordena todas as economias e une rotas da maior para a menor, **se** a carga couber (peso e volume) e a rota não passar da extensão máxima. Depois, o **2-opt** tenta inverter trechos de cada rota para desfazer cruzamentos.

A distância usa **haversine** (distância sobre a esfera) × 1,25 de sinuosidade. Em produção, use a matriz real de um motor de rotas (OSRM, Google, HERE)."""),
    code("""resultados = {km: mm.comparar_cenarios(km_max=km) for km in (500, 700, 900, 1_100, np.inf)}
resultados[900]"""),
    code("""v = mm.FROTA['Truck']
rotas = [mm.dois_opt(r, D) for r in mm.clarke_wright(kg, m3, D, v, km_max=900)]
detalhe = mm.avaliar_rotas(rotas, kg, m3, D, v, nomes, frota=mm.FROTA)
fig, ax = plt.subplots(figsize=(7.5, 7))
ax.scatter(C.lon[1:], C.lat[1:], s=kg[1:] / 40, color='#3b6ea5', alpha=.6, zorder=3)
ax.scatter(C.lon[0], C.lat[0], s=160, marker='*', color='#c0392b', zorder=4)
for r, cor in zip(rotas, plt.cm.tab10.colors * 3):
    cam = [0, *r, 0]
    ax.plot(C.lon[cam], C.lat[cam], color=cor, lw=1.3, alpha=.85)
for _, c in C.iterrows():
    ax.annotate(c.cidade.replace(' (hub)', ''), (c.lon, c.lat), fontsize=6.5, xytext=(3, 2), textcoords='offset points')
ax.set_title('Milk run a partir de Recife (extensão máx. 900 km)', loc='left'); ax.set_aspect('equal'); ax.axis('off')
detalhe[['veiculo', 'sequencia', 'km', 'kg', 'm3', 'ocupacao', 'horas', 'pernoites', 'custo']]"""),
    code("""pd.DataFrame({('∞' if not np.isfinite(k) else f'{k:,.0f} km'): r.loc['milk run + right-sizing', ['rotas', 'km', 'custo', 'ocupacao_media', 'maior_rota_h', 'pernoites']]
              for k, r in resultados.items()}).T"""),
    md("""🎯 **Leitura executiva**
- **Direto × milk run × veículo certo.** Com extensão máxima de 900 km, o milk run corta ~30% do custo diário em relação a "um caminhão por cidade", e **escolher o veículo certo para cada rota** corta mais ~20%. As duas alavancas se somam, e a segunda não exige nenhum algoritmo, só disciplina de planejamento.
- **A rota mais barata não é a melhor.** Sem limite de extensão, o custo cai ainda mais, mas a maior rota passa de **30 h**: a última cidade recebe no **segundo dia**, e a promessa D+1 do O2 quebra. **A extensão máxima da rota é uma decisão de serviço**, que tem que vir da promessa ao cliente, não do planejador de transporte.
- **Jornada é restrição, não detalhe.** Rotas acima de ~11 h exigem pernoite ou segundo motorista (o modelo cobra isso). ⚠️ As regras de jornada (Lei 13.103/2015 e convenções) devem ser validadas com o jurídico.
- **Cidades do sertão (Sousa, Patos, Mossoró, Serra Talhada)** geram as rotas longas. A alternativa estrutural é um **ponto de transbordo**: carreta cheia até ele e veículos menores na capilaridade. A seção 4 testa onde isso se paga.
- **Governança do contrapeso do O2:** custo/kg deve ser acompanhado **por região e com mix constante** (medida DAX `Custo por kg Mix Constante`). O ganho de roteirização aparece como queda real, e não se confunde com o efeito mix.
"""),

    md("## 4. Rede com transbordo · vale abrir um satélite? Onde?"),
    md("""🧠 **Por dentro da técnica · localização de instalações.** Um **satélite de transbordo** (cross-dock) recebe carretas cheias do hub e redistribui com veículos menores. Ele troca **km de caminhão meio vazio** por **custo fixo + manuseio + tempo de transbordo**. Para cada combinação de satélites candidatos (até 2 dos 4, isto é, 11 redes), o modelo:
1. atribui cada cidade à instalação mais próxima (hub ou satélite aberto);
2. calcula o line-haul hub → satélite em carretas (1 viagem ida e volta = meio dia de veículo);
3. roteiriza cada satélite com Clarke-Wright + 2-opt e veículo dimensionado por rota;
4. mede o **serviço**: hora de chegada em cada cidade desde a saída do hub, contra a janela de entrega (14 h).

Com poucos candidatos, a **enumeração completa** é a escolha certa: garante o ótimo dentro das premissas e é auditável. Com dezenas de candidatos, o problema vira um MILP de localização (*capacitated facility location*).

**Detalhe que muda o resultado:** o sentido em que uma rota é percorrida não muda o km, mas muda **quem recebe primeiro**. `_orientar` escolhe o sentido que entrega mais kg dentro da janela."""),
    code("""redes = mm.comparar_redes()
redes[['satelites', 'custo_dia', 'custo_transbordo_total', 'km', 'pernoites', 'pct_demanda_no_prazo', 'ultima_entrega_h', 'cidades_fora_do_prazo']]"""),
    code("""base = redes.set_index('satelites').loc['(sem transbordo)', 'custo_dia']
fig, ax = plt.subplots(figsize=(9, 4.4))
cor = ['#c0392b' if s == '(sem transbordo)' else '#2e8b57' if c < base else '#7f8c8d' for s, c in zip(redes.satelites, redes.custo_dia)]
ax.scatter(redes.custo_dia / 1e3, redes.pct_demanda_no_prazo, s=70, c=cor)
for _, r in redes.iterrows():
    ax.annotate(r.satelites, (r.custo_dia / 1e3, r.pct_demanda_no_prazo), fontsize=7, xytext=(4, 3), textcoords='offset points')
ax.axvline(base / 1e3, color='#c0392b', ls=':', lw=1)
ax.set_xlabel('custo da rede (R$ mil/dia)'); ax.set_ylabel('demanda entregue na janela de 14 h')
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{v:.0%}'))
ax.set_title('Custo × serviço das configurações de rede (verde = mais barata que sem transbordo)', loc='left')"""),
    md("""🎯 **Transbordo só se paga longe do hub.** O satélite em **Patos**, no sertão, é a única configuração **mais barata** que a rede atual (−11,5%, com pernoites caindo de 8 para 4): a carreta cheia substitui várias viagens longas de caminhão meio vazio. Satélites em **Caruaru** ou **Campina Grande**, a ~150–180 km de Recife, **encarecem** a rede (+8% a +15%): a distância economizada não paga custo fixo, manuseio e a viagem extra da carreta. Eles até melhoram o prazo, mas a um custo que outra alavanca resolve mais barato (a seguir)."""),
    code("""from dataclasses import replace
cen = {f'{h} h antes': mm.avaliar_rede(['Patos'], p=mm.ParametrosRede(antecipacao_linehaul_h=h)) for h in (0, 2, 3)}
pd.DataFrame({k: {'custo_dia': v['custo_dia'], 'pct_no_prazo': v['pct_demanda_no_prazo'], 'ultima_entrega_h': v['ultima_entrega_h'],
                  'fora_do_prazo': v['cidades_fora_do_prazo'] or '—'} for k, v in cen.items()}).T"""),
    md("""🎯 **A onda antecipada fecha o gap de serviço sem custo.** Com o satélite em Patos, Arcoverde fica fora da janela. Fazer a carreta do satélite sair **3 h antes** da onda geral do hub (primeira onda de separação dedicada ao satélite) leva o atendimento a **100% no prazo** com o **mesmo custo**. É uma decisão de **sequenciamento de ondas no CD**, não de transporte: o middle mile se resolve dentro do armazém. (Premissa: o CD consegue antecipar a separação desse volume; validar com a capacidade de onda do SC-009.)"""),
    code("""sens = pd.DataFrame([{'custo_fixo_satelite_dia': fx,
                      'variacao_vs_rede_atual': mm.avaliar_rede(['Patos'], p=mm.ParametrosRede(custo_fixo_satelite_dia=fx))['custo_dia'] / base - 1}
                     for fx in (2_500, 5_000, 7_500, 8_000, 8_500, 10_000)])
sens"""),
    md("""🎯 **Robustez da decisão.** A premissa de custo fixo do satélite é R$ 2.500/dia, mas **a decisão só se inverte acima de ~R$ 8.200/dia**: há margem de mais de 3× para erro de estimativa. É assim que se apresenta uma recomendação de rede a um comitê: **decisão + ponto de virada**, não só o número do cenário base.

**Recomendação para o comitê (caso Vértice):**
1. Abrir **satélite de transbordo em Patos (PB)** para o sertão (Sousa, Caicó, Mossoró, Serra Talhada, Arcoverde).
2. Criar **onda antecipada** no hub para a carreta do satélite (−3 h).
3. Manter capitais e agreste atendidos direto do hub, com **veículo dimensionado por rota**.
4. Acompanhar **custo/kg por região com mix constante** (DAX `Custo por kg Mix Constante`) e **MM-013** (rotas acima da jornada) como contrapeso.

---
*KPIs: MM-003 (ocupação na restrição ativa), MM-004 (custo/kg), MM-011 (paradas por rota), MM-012 (volume despachado no prazo), MM-013 (rotas acima da jornada). Material de portfólio com premissas declaradas.*"""),
]
