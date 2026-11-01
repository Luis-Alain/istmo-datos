"""Pipeline completo: Excel → limpieza y reglas → SQLite."""

import logging

from istmo_datos.calidad import aplicar_reglas, limpiar_texto
from istmo_datos.carga import cargar_base
from istmo_datos.config import DB, PROCESADOS, RAW
from istmo_datos.extraer import extraer

log = logging.getLogger("istmo_datos")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    crudo, metas = extraer(RAW)
    log.info("Extraídas %d filas de %s", len(crudo), RAW.name)

    ventas, incidencias = aplicar_reglas(limpiar_texto(crudo))

    resumen = ventas.groupby("estado").venta_neta.agg(["count", "sum"]).round(2)
    log.info("Resumen por estado:\n%s", resumen)

    # Control de cuadratura: nada se pierde en el camino.
    assert len(ventas) == len(crudo), "Se perdieron filas durante la transformación"

    PROCESADOS.mkdir(parents=True, exist_ok=True)
    ventas.to_csv(PROCESADOS / "ventas_procesadas.csv", index=False)
    incidencias.to_csv(PROCESADOS / "incidencias.csv", index=False)

    cargar_base(crudo, ventas, incidencias, metas)
    log.info("Base de datos lista: %s", DB)


if __name__ == "__main__":
    main()
