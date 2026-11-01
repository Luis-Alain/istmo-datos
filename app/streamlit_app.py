import sqlite3

import pandas as pd
import plotly.express as px
import streamlit as st

from istmo_datos.config import ANIO_META, DB, MES_META

st.set_page_config(page_title="Distribuidora Istmo: Ventas", layout="wide")


@st.cache_data
def cargar() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    con = sqlite3.connect(DB)
    try:
        ventas = pd.read_sql(
            """SELECT f.id_venta_origen AS id_venta, d.fecha, s.nombre AS sucursal,
                      p.nombre AS producto, p.categoria, f.cantidad,
                      f.venta_neta, f.estado, f.motivo
               FROM fact_ventas f
               JOIN dim_fecha d USING (fecha_id)
               JOIN dim_sucursal s USING (sucursal_id)
               JOIN dim_producto p USING (producto_id)""",
            con,
            parse_dates=["fecha"],
        )
        metas = pd.read_sql(
            """SELECT s.nombre AS sucursal, m.meta_mensual
               FROM fact_meta m JOIN dim_sucursal s USING (sucursal_id)
               WHERE m.anio = ? AND m.mes = ?""",
            con,
            params=(ANIO_META, MES_META),
        )
        inc = pd.read_sql("SELECT * FROM incidencias", con)
    finally:
        con.close()
    return ventas, metas, inc


if not DB.exists():
    st.error("No existe la base de datos. Ejecuta primero: `uv run etl`")
    st.stop()

ventas, metas, inc = cargar()

# ---- Filtros ----
st.sidebar.header("Filtros")
rango = st.sidebar.date_input("Fecha", (ventas.fecha.min(), ventas.fecha.max()))
opciones_suc = sorted(ventas.sucursal.unique())
opciones_cat = sorted(ventas.categoria.unique())
sucs = st.sidebar.multiselect("Sucursal", opciones_suc, default=opciones_suc)
cats = st.sidebar.multiselect("Categoría", opciones_cat, default=opciones_cat)
if len(rango) == 2:
    ini, fin = map(pd.Timestamp, rango)
    ventas = ventas[ventas.fecha.between(ini, fin)]
ventas = ventas[ventas.sucursal.isin(sucs) & ventas.categoria.isin(cats)]
ok = ventas[ventas.estado == "ACEPTADO"]
pendientes = ventas[ventas.estado == "PENDIENTE"]

st.title("Distribuidora Istmo S.A.: Ventas netas")
st.caption("Muestra del 1 al 6 de septiembre de 2026. Solo registros ACEPTADOS salvo indicación.")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Ventas netas aceptadas (USD)", f"{ok.venta_neta.sum():,.2f}")
c2.metric("Registros aceptados", len(ok))
c3.metric("Registros pendientes", len(pendientes))
c4.metric("Valor en revisión (USD)", f"{pendientes.venta_neta.sum():,.2f}")

# ---- Ventas por sucursal y categoría ----
col_a, col_b = st.columns(2)
por_sucursal = ok.groupby("sucursal", as_index=False).venta_neta.sum()
col_a.plotly_chart(
    px.bar(
        por_sucursal,
        x="venta_neta",
        y="sucursal",
        orientation="h",
        text_auto=True,
        title="Ventas netas por sucursal (USD)",
        labels={"venta_neta": "Ventas netas (USD)", "sucursal": "Sucursal"},
    ),
    width="stretch",
)
por_categoria = ok.groupby("categoria", as_index=False).venta_neta.sum()
col_b.plotly_chart(
    px.bar(
        por_categoria,
        x="categoria",
        y="venta_neta",
        text_auto=True,
        title="Ventas netas por categoría (USD)",
        labels={"venta_neta": "Ventas netas (USD)", "categoria": "Categoría"},
    ),
    width="stretch",
)

# ---- Ventas vs metas (solo sucursales con meta) ----
st.subheader("Avance de la muestra frente a la meta mensual")
comparacion = metas.merge(por_sucursal, on="sucursal", how="left").fillna({"venta_neta": 0})
comparacion["avance_%"] = (comparacion.venta_neta / comparacion.meta_mensual * 100).round(1)
st.dataframe(
    comparacion.rename(
        columns={"venta_neta": "Ventas muestra (USD)", "meta_mensual": "Meta mensual (USD)"}
    )
)
st.warning(
    "La muestra cubre 6 de 30 días y no es el total del mes: este avance NO es cumplimiento. "
    "Faltan metas de 9 sucursales."
)

# ---- Incidencias ----
st.subheader("Incidencias de calidad de datos")
st.dataframe(inc)

with st.expander("Datos que faltan para completar el análisis"):
    st.markdown(
        "- Inventario completo\n- Pedidos de la API en línea\n- Ventas de septiembre 2025\n"
        "- Metas de las 9 sucursales restantes\n- Confirmación de V006, V010, V002 y V008"
    )
