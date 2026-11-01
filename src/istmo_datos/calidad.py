"""Transformación: reglas de calidad R1-R6, venta neta y estado por registro."""

import pandas as pd

from istmo_datos.config import SUCURSALES_CONOCIDAS, VALORES_VACIOS

# Prioridad de estados: gana el más restrictivo.
ORDEN = {"ACEPTADO": 0, "CORREGIDO": 0, "PENDIENTE": 1, "EXCLUIDO_PROVISIONAL": 2}

ACCIONES = {
    "R1": "Confirmar con el ERP si hubo doble captura; reincorporar solo si es una venta distinta",
    "R2": "Verificar con la sucursal si la venta existió; corregir la cantidad en el ERP",
    "R3": "Validar si es una devolución; si lo es, registrarla como documento de devolución",
    "R4": "Consultar al responsable del dato en el ERP para completar el campo",
    "R5": "Confirmar el nombre oficial; no se asume que sea otra sucursal",
    "R6": "Revisar el descuento aplicado con la sucursal",
}


def limpiar_texto(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza tipos. Los valores inválidos quedan como NaN/NaT, no se eliminan."""
    df = df.copy()
    for c in ["sucursal", "producto", "categoria"]:
        df[c] = df[c].str.strip().replace(dict.fromkeys(VALORES_VACIOS, ""))
    df["fecha"] = pd.to_datetime(df["fecha"], format="%d/%m/%Y", errors="coerce")
    for c in ["cantidad", "precio", "descuento"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def cargar(ruta) -> pd.DataFrame:
    """extrae y limpia tipos."""
    from istmo_datos.extraer import extraer

    ventas, _ = extraer(ruta)
    return limpiar_texto(ventas)


def aplicar_reglas(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Calcula venta neta y asigna estado. Devuelve (ventas, incidencias)."""
    df = df.copy().reset_index(drop=True)
    df["venta_neta"] = (df["cantidad"] * df["precio"] - df["descuento"]).round(2)
    df["estado"] = "ACEPTADO"
    df["motivo"] = ""
    columnas_dup = [
        "id_venta",
        "fecha",
        "sucursal",
        "producto",
        "categoria",
        "cantidad",
        "precio",
        "descuento",
    ]
    duplicada = df.duplicated(subset=columnas_dup, keep="first")
    df["es_duplicado"] = duplicada
    incidencias: list[dict] = []

    def registrar(i: int, regla: str, estado: str, motivo: str) -> None:
        incidencias.append(
            {
                "id_venta": df.at[i, "id_venta"],
                "fila_origen": df.at[i, "fila_origen"] if "fila_origen" in df else i + 2,
                "regla": regla,
                "estado": estado,
                "motivo": motivo,
                "venta_neta": df.at[i, "venta_neta"],
                "accion_sugerida": ACCIONES[regla],
                "revision": "ABIERTA",
            }
        )
        if ORDEN[estado] > ORDEN[str(df.at[i, "estado"])]:
            df.at[i, "estado"] = estado
        df.at[i, "motivo"] = (str(df.at[i, "motivo"]) + "; " + motivo).strip("; ")

    # El índice es 0..n-1 tras reset_index, así que la posición coincide con la etiqueta.
    for i, fila in enumerate(df.to_dict("records")):
        if duplicada[i]:
            registrar(i, "R1", "EXCLUIDO_PROVISIONAL", "Fila duplicada; se conserva la primera")
        cantidad = fila["cantidad"]
        if pd.notna(cantidad) and cantidad == 0:
            registrar(i, "R2", "EXCLUIDO_PROVISIONAL", "Cantidad cero")
        elif pd.notna(cantidad) and cantidad < 0:
            registrar(i, "R3", "PENDIENTE", "Cantidad negativa: validar si es devolución")
        for campo in ["sucursal", "producto", "fecha", "precio"]:
            valor = fila[campo]
            if pd.isna(valor) or valor == "":
                registrar(i, "R4", "PENDIENTE", f"Campo vacío: {campo}")
        sucursal = fila["sucursal"]
        if sucursal != "" and not pd.isna(sucursal) and sucursal not in SUCURSALES_CONOCIDAS:
            registrar(i, "R5", "PENDIENTE", f"Sucursal no reconocida: {sucursal}")
        bruto = fila["cantidad"] * fila["precio"]
        if pd.notna(bruto) and bruto > 0 and fila["descuento"] > bruto:
            registrar(i, "R6", "PENDIENTE", "Descuento mayor al valor bruto")

    columnas_inc = [
        "id_venta",
        "fila_origen",
        "regla",
        "estado",
        "motivo",
        "venta_neta",
        "accion_sugerida",
        "revision",
    ]
    return df, pd.DataFrame(incidencias, columns=columnas_inc)
