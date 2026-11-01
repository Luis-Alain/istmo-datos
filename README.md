# istmo-datos

Taller de Sistemas de Información, Unidad 3 (UTP): integración, calidad y análisis de ventas de Distribuidora Istmo S.A.

Flujo: **Excel (datos crudos) → Python (extracción) → reglas de calidad → SQLite (modelo en estrella) → reporte en Streamlit**.

## Requisitos

- [uv](https://docs.astral.sh/uv/) (instala Python 3.12 automáticamente si hace falta)
- Docker (opcional)

## Uso

```bash
uv sync                                      # crea el entorno desde uv.lock
uv run etl                                   # extrae, depura y carga db/istmo.db
uv run streamlit run app/streamlit_app.py    # reporte en http://localhost:8501
uv run pytest                                # pruebas
uv run ruff check . && uv run ruff format .  # lint y formato
```

## Docker

```bash
docker compose up --build                    # reporte en http://localhost:8501
```

La imagen ejecuta el ETL al construirse, así que el contenedor ya trae la base de datos lista.

## Estructura

```
src/istmo_datos/   extraer.py · calidad.py · carga.py · etl.py · config.py
app/               streamlit_app.py
db/schema.sql      modelo en estrella (dim_fecha, dim_sucursal, dim_producto, fact_ventas, fact_meta)
data/raw/          ventas_septiembre_2026.xlsx (hojas: ventas, metas)
tests/             reglas de calidad y modelo
```

## Resultados de control (muestra del 1 al 6 de septiembre de 2026)

| Estado | Registros | Venta neta (USD) |
| --- | --- | --- |
| ACEPTADO | 6 | 158.30 |
| PENDIENTE | 4 | 74.25 |
| EXCLUIDO_PROVISIONAL | 2 | 29.20 |

Ningún registro se elimina: todos conservan estado y motivo, y las incidencias quedan en la tabla `incidencias` con su fila de origen en el Excel.

## Limitaciones

La muestra no incluye inventario, pedidos de la API, ventas de septiembre 2025 ni metas de 9 de las 12 sucursales. El avance contra la meta es de la muestra, no cumplimiento mensual.
