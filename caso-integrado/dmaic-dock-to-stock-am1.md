# A3 · DMAIC Dock-to-stock CD-AM1 (Manaus)

> Projeto fictício do caso Vértice. Análise completa e reproduzível em [`notebooks/dmaic_dock_to_stock_am1.ipynb`](../notebooks/dmaic_dock_to_stock_am1.ipynb). Dados: `dados/fato_recebimentos_am1.csv`.

| Contexto | Meta |
|---|---|
| O CD-AM1 viabiliza a promessa de prazo no Norte (O2), mas era o único CD **não capaz** contra o SLA de dock-to-stock de 12 h. | P90 ≤ 6 h e Ppk ≥ 1,0 (percentis) até set/2026, sem perder acurácia de inventário (contrapeso) |

## Situação atual (Medir · fev–mar/2026, 1.154 recebimentos)
- Mediana de 5,1 h · **P90 de 9,6 h** · **5,1% fora do SLA (~51 mil PPM)**
- **Ppk (percentis) = 0,44.** O Ppk "normal" daria 0,68 e superestimaria a capacidade, porque o tempo tem cauda longa.

## Análise
| Evidência | Resultado |
|---|---|
| Pareto das horas **totais** | Espera na doca, 36% |
| Pareto das horas **acima do SLA** | **Tratativa de divergência, 46%**: a cauda tem causa diferente da média |
| Agendado × não agendado | P90 de 6,8 h × 10,7 h (Mann-Whitney p < 0,001) |
| Divergência por fornecedor | F07 (36%) e F03 (32%) contra ~14% dos demais (χ², p < 0,001) |
| Regressão log (R² 0,60) | Divergência +81% · não agendado +71% · carga batida +33% · sem ASN +10% |
| Turno de chegada | Sem evidência (p = 0,09; só 3 cargas noturnas: cautela) |

**Causa raiz:** a regra do WMS trava a NF inteira quando há qualquer item divergente, e o CD novo não tinha dono do processo de recebimento.

## Contramedidas (piloto jun–jul/2026)
1. **Recebimento parcial:** libera o conforme e segrega só o divergente (regra de WMS)
2. **Agendamento obrigatório** por janela no portal do fornecedor
3. **ASN/XML antecipado + conferência cega** por scanner
4. **Desenvolvimento de fornecedor** F03/F07 (paletização padrão)

## Resultado
| | Medir | Piloto | Controle |
|---|---|---|---|
| P90 (h) | 9,6 | **4,9** (−49%) | 5,0 |
| Fora do SLA | 5,1% | 0,09% | 0,08% |
| Ppk (percentis) | 0,44 | **1,18** | 1,01 |

Mann-Whitney unilateral p < 0,001; Levene p < 0,001 (a variação também caiu). Nos 54 dias de controle, nenhum ponto saiu dos limites congelados do piloto. No painel da rede, o **SC-006 do CD-AM1** cai de 7,6 h (2T26) para 5,0 h (3T26).

## Controle e próximos passos
- Plano de controle com o dono do processo (gerente do CD-AM1): carta I do P90 diário, % agendados, % ASN, divergência F03/F07 e o contrapeso de acurácia de inventário.
- **Benefício estimado:** ~R$ 0,4 mi/ano em margem de vendas não perdidas, calculado com premissas D (valor médio da NF, probabilidade de ruptura). ⚠️ Precisa da validação da Controladoria antes de entrar em hard savings (LS-101).
- **Yokoten:** as contramedidas 1 e 3 são regras de sistema, replicáveis nos demais CDs com custo marginal baixo.
