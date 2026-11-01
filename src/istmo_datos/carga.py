"""Carga: guarda crudo, dimensiones, hechos, metas e incidencias en SQLite."""

import sqlite3
from pathlib import Path

import pandas as pd

from istmo_datos.config import ANIO_META, DB, MES_META, SCHEMA, SUCURSALES_CONOCIDAS

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def _nan_a_none(valor):
    return None if pd.isna(valor) else valor


def cargar_base(
    crudo: pd.DataFrame,
    ventas: pd.DataFrame,
    incidencias: pd.DataFrame,
    metas: pd.DataFrame,
    ruta_db: Path = DB,
) -> None:
    ruta_db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(ruta_db)
    try:
        # 1. Copia cruda sin modificar: evidencia de lo que llegó.
        crudo.to_sql("stg_ventas_raw", con, if_exists="replace", index=False)

        # 2. Esquema (recrea las tablas del modelo: la carga es idempotente).
        con.executescript(SCHEMA.read_text(encoding="utf-8"))

        # 3. Dimensiones.
        sucursales = ["SIN ASIGNAR", *sorted(SUCURSALES_CONOCIDAS)]
        con.executemany(
            "INSERT INTO dim_sucursal (sucursal_id, nombre) VALUES (?, ?)",
            list(enumerate(sucursales)),
        )
        id_sucursal = {nombre: i for i, nombre in enumerate(sucursales)}

        # Solo entran a los hechos filas con los campos mínimos y que no sean duplicados.
        cargables = ventas[
            ~ventas["es_duplicado"]
            & ventas["fecha"].notna()
            & ventas["cantidad"].notna()
            & ventas["precio"].notna()
            & (ventas["producto"] != "")
        ].copy()

        productos = cargables[["producto", "categoria"]].drop_duplicates("producto")
        con.executemany(
            "INSERT INTO dim_producto (producto_id, nombre, categoria) VALUES (?, ?, ?)",
            [(i + 1, r.producto, r.categoria) for i, r in enumerate(productos.itertuples())],
        )
        id_producto = {r.producto: i + 1 for i, r in enumerate(productos.itertuples())}

        fechas = sorted(cargables["fecha"].dt.normalize().unique())
        filas_fecha = []
        for f in map(pd.Timestamp, fechas):
            filas_fecha.append(
                (
                    int(f.strftime("%Y%m%d")),
                    f.strftime("%Y-%m-%d"),
                    f.year,
                    f.month,
                    f.day,
                    DIAS[f.weekday()],
                )
            )
        con.executemany("INSERT INTO dim_fecha VALUES (?, ?, ?, ?, ?, ?)", filas_fecha)

        # 4. Hechos.
        filas = []
        for r in cargables.to_dict("records"):
            filas.append(
                (
                    r["id_venta"],
                    "ERP",
                    int(r["fila_origen"]),
                    int(r["fecha"].strftime("%Y%m%d")),
                    id_sucursal.get(r["sucursal"], 0),
                    r["sucursal"],
                    id_producto[r["producto"]],
                    int(r["cantidad"]),
                    float(r["precio"]),
                    float(_nan_a_none(r["descuento"]) or 0),
                    float(r["venta_neta"]),
                    r["estado"],
                    r["motivo"],
                )
            )
        con.executemany(
            """INSERT INTO fact_ventas
               (id_venta_origen, fuente, fila_origen, fecha_id, sucursal_id, sucursal_original,
                producto_id, cantidad, precio_unitario, descuento, venta_neta, estado, motivo)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            filas,
        )

        # 5. Metas (solo sucursales con meta entregada).
        for r in metas.to_dict("records"):
            if r["sucursal"] in id_sucursal:
                con.execute(
                    "INSERT INTO fact_meta VALUES (?, ?, ?, ?)",
                    (id_sucursal[r["sucursal"]], ANIO_META, MES_META, float(r["meta_mensual"])),
                )

        # 6. Incidencias.
        incidencias.to_sql("incidencias_tmp", con, if_exists="replace", index=False)
        con.execute(
            """INSERT INTO incidencias
               (id_venta, fila_origen, regla, estado, motivo, venta_neta, accion_sugerida, revision)
               SELECT id_venta, fila_origen, regla, estado, motivo, venta_neta,
                      accion_sugerida, revision FROM incidencias_tmp"""
        )
        con.execute("DROP TABLE incidencias_tmp")
        con.commit()
    finally:
        con.close()
