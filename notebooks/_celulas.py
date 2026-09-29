"""Utilitários para montar e executar notebooks a partir de listas de células."""

from pathlib import Path

import nbformat as nbf
from nbconvert.preprocessors import ExecutePreprocessor

AQUI = Path(__file__).resolve().parent
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell


def executar(nome: str, celulas: list) -> Path:
    """Executa as células num kernel novo e salva o .ipynb com as saídas (legível no GitHub)."""
    nb = nbf.v4.new_notebook(
        cells=celulas, metadata={"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}}
    )
    ExecutePreprocessor(timeout=900, kernel_name="python3").preprocess(nb, {"metadata": {"path": str(AQUI)}})
    destino = AQUI / f"{nome}.ipynb"
    nbf.write(nb, destino)
    return destino
