"""Extracción: lee la hoja de Excel tal cual, todo como texto."""

from pathlib import Path

import pandas as pd

from istmo_datos.config import RAW


def extraer(ruta: Path = RAW) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve (ventas_crudas, metas). Nada se corrige aquí."""
    ventas = pd.read_excel(ruta, sheet_name="ventas", dtype=str, keep_default_na=False)
    ventas.columns = [c.strip().lower().replace(" ", "_") for c in ventas.columns]
    ventas["fila_origen"] = ventas.index + 2  # fila real en la hoja (fila 1 = encabezado)
    ventas["archivo_origen"] = Path(ruta).name
    metas = pd.read_excel(ruta, sheet_name="metas")
    metas.columns = [c.strip().lower().replace(" ", "_") for c in metas.columns]
    return ventas, metas
