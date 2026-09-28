"""Gera e executa os notebooks do repositório (as saídas ficam salvas para leitura no GitHub).

Uso:
    python notebooks/gerar_notebook.py            # todos
    python notebooks/gerar_notebook.py pessoas    # só um (caso_vertice | pessoas | dmaic | middle_mile)
"""
import sys

import nb_caso_vertice
import nb_dmaic
import nb_middle_mile
import nb_pessoas
from _celulas import executar

NOTEBOOKS = {
    "caso_vertice": nb_caso_vertice.CELULAS,
    "pessoas": nb_pessoas.CELULAS,
    "dmaic": nb_dmaic.CELULAS,
    "middle_mile": nb_middle_mile.CELULAS,
}
ARQUIVOS = {"caso_vertice": "caso_vertice", "pessoas": "pessoas_forca_de_trabalho",
            "dmaic": "dmaic_dock_to_stock_am1", "middle_mile": "middle_mile_consolidacao_rotas"}

if __name__ == "__main__":
    for nome in sys.argv[1:] or NOTEBOOKS:
        print("ok:", executar(ARQUIVOS[nome], NOTEBOOKS[nome]))
