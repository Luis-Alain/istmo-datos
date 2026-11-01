"""Rutas y constantes del proyecto."""

import os
from pathlib import Path

# Raíz del proyecto. ISTMO_RAIZ permite fijarla en contenedores o instalaciones no editables.
RAIZ = Path(os.environ.get("ISTMO_RAIZ", Path(__file__).resolve().parents[2]))
RAW = RAIZ / "data" / "raw" / "ventas_septiembre_2026.xlsx"
PROCESADOS = RAIZ / "data" / "processed"
DB = RAIZ / "db" / "istmo.db"
SCHEMA = RAIZ / "db" / "schema.sql"

# Catálogo de sucursales reconocidas. Solo las que aparecen con datos/metas en el taller:
# no se inventan las otras 9 sucursales de la empresa.
SUCURSALES_CONOCIDAS = frozenset({"David Centro", "Boquete", "Bugaba"})

# Valores de texto que significan "campo vacío" en la hoja de origen.
VALORES_VACIOS = {"(vacío)", "(vacio)", "N/A", "NA", "-"}

ANIO_META, MES_META = 2026, 9
