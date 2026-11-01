import pandas as pd
import pytest

from istmo_datos.calidad import aplicar_reglas, limpiar_texto
from istmo_datos.config import RAW
from istmo_datos.extraer import extraer


def _procesar_muestra():
    crudo, _ = extraer(RAW)
    return aplicar_reglas(limpiar_texto(crudo))


def _fila(**campos) -> pd.DataFrame:
    """Un registro mínimo válido, sobrescribible por regla."""
    base = {
        "id_venta": "T001",
        "fecha": "01/09/2026",
        "sucursal": "Boquete",
        "producto": "Arroz 5 lb",
        "categoria": "Abarrotes",
        "cantidad": "2",
        "precio": "4.50",
        "descuento": "0",
        "fila_origen": 2,
    }
    base.update(campos)
    return pd.DataFrame([base])


def _reglas(df: pd.DataFrame) -> set[str]:
    _, inc = aplicar_reglas(limpiar_texto(df))
    return set(inc["regla"])


def test_totales_de_control():
    ventas, _ = _procesar_muestra()
    por_estado = ventas.groupby("estado").venta_neta.sum().round(2)
    assert len(ventas) == 12
    assert por_estado["ACEPTADO"] == 158.30
    assert por_estado["PENDIENTE"] == 74.25
    assert por_estado["EXCLUIDO_PROVISIONAL"] == 29.20


def test_ninguna_fila_se_elimina():
    crudo, _ = extraer(RAW)
    ventas, _ = _procesar_muestra()
    assert len(ventas) == len(crudo)


def test_duplicado_se_excluye_y_se_conserva_el_primero():
    ventas, _ = _procesar_muestra()
    assert ventas[ventas.id_venta == "V005"].estado.tolist() == ["ACEPTADO", "EXCLUIDO_PROVISIONAL"]


def test_ventas_por_sucursal_aceptadas():
    ventas, _ = _procesar_muestra()
    ok = ventas[ventas.estado == "ACEPTADO"]
    por_sucursal = ok.groupby("sucursal").venta_neta.sum().round(2).to_dict()
    assert por_sucursal == {"David Centro": 72.00, "Boquete": 44.10, "Bugaba": 42.20}


def test_formula_venta_neta():
    ventas, _ = aplicar_reglas(limpiar_texto(_fila(cantidad="10", precio="3.25", descuento="1")))
    assert ventas.venta_neta.iloc[0] == 31.50


def test_r2_cantidad_cero():
    ventas, _ = aplicar_reglas(limpiar_texto(_fila(cantidad="0")))
    assert ventas.estado.iloc[0] == "EXCLUIDO_PROVISIONAL"


def test_r3_cantidad_negativa_queda_pendiente():
    ventas, inc = aplicar_reglas(limpiar_texto(_fila(cantidad="-2")))
    assert ventas.estado.iloc[0] == "PENDIENTE"
    assert "R3" in set(inc["regla"])


@pytest.mark.parametrize("texto", ["", "(vacío)"])
def test_r4_sucursal_vacia(texto):
    assert "R4" in _reglas(_fila(sucursal=texto))


def test_r5_sucursal_no_reconocida():
    assert "R5" in _reglas(_fila(sucursal="Sucursal Centro"))


def test_r6_descuento_mayor_al_bruto():
    assert "R6" in _reglas(_fila(cantidad="1", precio="2.00", descuento="5"))


def test_registro_limpio_no_genera_incidencias():
    ventas, inc = aplicar_reglas(limpiar_texto(_fila()))
    assert ventas.estado.iloc[0] == "ACEPTADO"
    assert inc.empty
