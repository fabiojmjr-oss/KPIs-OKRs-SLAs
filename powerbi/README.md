# Power BI · Modelo do caso Vértice

O repositório não versiona um `.pbix` (binário, ruim de revisar em Git). Ele entrega tudo o que é preciso para montar o relatório em ~30 minutos, de forma reprodutível: dados, modelo, medidas e tema.

## 1. Dados
CSVs em [`../dados/`](../dados/), gerados por `python -m kpikit.simulador`. Delimitador vírgula, decimal ponto, UTF-8. No Power Query, use *Localidade: Inglês (EUA)* para ler os decimais corretamente.

## 2. Modelo (estrela com um floco)

```
                     dim_calendario[data]
          ┌──────────────┬──────┴───────┬───────────────┬──────────────┐
      fato_cd        fato_hub     fato_last_mile    fato_linehaul   fato_demanda   fato_midia
          │              │              │                 │              │
          └──── dim_unidade[unidade_id] ┘                 └── dim_regiao[regiao_id] ──┘
                         │                                        ▲
                         └──────────── regiao_id ─────────────────┘
      fato_pessoas[mes] → dim_calendario[data]   ·   fato_pessoas[unidade_id] → dim_unidade
```

| Relação | Cardinalidade | Filtro |
|---|---|---|
| dim_calendario[data] → fatos[data] | 1:N | único |
| dim_unidade[unidade_id] → fato_cd / fato_hub / fato_last_mile / fato_pessoas | 1:N | único |
| dim_regiao[regiao_id] → dim_unidade, fato_linehaul, fato_demanda | 1:N | único |

| dim_unidade[unidade_id] → fato_colaboradores (1 linha por admissão) | 1:N | único; relacione `data_admissao` à dim_calendario como relação **ativa** e `data_desligamento` como **inativa** (use `USERELATIONSHIP`) |
| fato_recebimentos_am1 | — | tabela do estudo DMAIC (nível recebimento); use sozinha ou relacione a data de `chegada` à dim_calendario |

Marque `dim_calendario` como **tabela de datas**.

## 3. Medidas
Cole [`medidas.dax`](medidas.dax) numa tabela `_Medidas`. Destaques:
- **`Custo por kg Mix Constante`** separa ganho de eficiência de efeito mix geográfico. É o antídoto para o contrapeso "violado" do O2 no notebook.
- **`Nota KR OTD`** reproduz em DAX a mesma fórmula de nota de `kpikit/okr.py`.

## 4. Páginas sugeridas
| Página | Visuais |
|---|---|
| Executivo | Cartões dos 9 KPIs estratégicos (valor · linha de base · meta · benchmark) com `Cor Status` na formatação condicional |
| Rede nacional | Mapa por UF/região com LM-011 e LM-001; linha mensal por região com linha constante de 77% (MELI 2T26) |
| CD | Matriz unidade × mês (SC-009, SC-007, SC-006); dispersão utilização × cut-off, que mostra a quebra não linear acima de ~90% |
| Middle mile | OTD-p/OTA, dwell por hub, custo/kg real vs. mix constante |
| Marketing | ROAS × POAS × MER mensal; tabela por canal |
| OKRs | Tabela de KRs com barra de dados na nota |

## 5. Tema
Importe [`tema-vertice.json`](tema-vertice.json) em *Exibir → Temas → Procurar temas*.

> Para CEP e otimização, use o app Streamlit e o notebook. No Power BI, visuais Python são possíveis, mas não funcionam no serviço sem gateway pessoal.
