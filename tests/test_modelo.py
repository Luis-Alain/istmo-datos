import sqlite3

import pytest

from istmo_datos.calidad import aplicar_reglas, limpiar_texto
from istmo_datos.carga import cargar_base
from istmo_datos.config import RAW
from istmo_datos.extraer import extraer


@pytest.fixture()
def con(tmp_path):
    crudo, metas = extraer(RAW)
    ventas, inc = aplicar_reglas(limpiar_texto(crudo))
    ruta = tmp_path / "test.db"
    cargar_base(crudo, ventas, inc, metas, ruta_db=ruta)
    conexion = sqlite3.connect(ruta)
    yield conexion
    conexion.close()


def test_consulta_ventas_por_sucursal(con):
    filas = con.execute(
        """SELECT s.nombre, ROUND(SUM(f.venta_neta), 2)
           FROM fact_ventas f JOIN dim_sucursal s USING (sucursal_id)
           WHERE f.estado = 'ACEPTADO' GROUP BY s.nombre ORDER BY 2 DESC"""
    ).fetchall()
    assert filas == [("David Centro", 72.0), ("Boquete", 44.1), ("Bugaba", 42.2)]


def test_el_duplicado_no_entra_a_hechos(con):
    n = con.execute("SELECT COUNT(*) FROM fact_ventas WHERE id_venta_origen = 'V005'").fetchone()[0]
    assert n == 1


def test_clave_unica_rechaza_doble_conteo(con):
    with pytest.raises(sqlite3.IntegrityError):
        con.execute(
            """INSERT INTO fact_ventas (id_venta_origen, fuente, fecha_id, sucursal_id,
               producto_id, cantidad, precio_unitario, descuento, venta_neta, estado)
               VALUES ('V001', 'ERP', 20260901, 1, 1, 1, 1, 0, 1, 'ACEPTADO')"""
        )


def test_crudo_se_conserva_completo(con):
    assert con.execute("SELECT COUNT(*) FROM stg_ventas_raw").fetchone()[0] == 12


def test_metas_solo_de_tres_sucursales(con):
    assert con.execute("SELECT COUNT(*) FROM fact_meta").fetchone()[0] == 3
