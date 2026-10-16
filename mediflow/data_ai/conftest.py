"""Agregado por Edil: ejecutar juntas las entregas sin instalar paquetes nuevos."""
import sys
from pathlib import Path

# Las pruebas originales usan imports directos; conservarlos y hacerlos portables.
data_ai_dir = Path(__file__).resolve().parent
for directory in (data_ai_dir.parents[1], data_ai_dir.parent / "backend", data_ai_dir):
    directory_text = str(directory)
    if directory_text not in sys.path:
        sys.path.insert(0, directory_text)
