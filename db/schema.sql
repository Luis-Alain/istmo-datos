-- Modelo en estrella (datamart de ventas). Grano de fact_ventas: una línea de venta
-- (un producto, en una sucursal, en una fecha) identificada por su ID de origen.

DROP TABLE IF EXISTS incidencias;
DROP TABLE IF EXISTS fact_meta;
DROP TABLE IF EXISTS fact_ventas;
DROP TABLE IF EXISTS dim_producto;
DROP TABLE IF EXISTS dim_sucursal;
DROP TABLE IF EXISTS dim_fecha;

CREATE TABLE dim_fecha (
  fecha_id   INTEGER PRIMARY KEY,          -- 20260901
  fecha      DATE NOT NULL UNIQUE,
  anio       INTEGER NOT NULL,
  mes        INTEGER NOT NULL,
  dia        INTEGER NOT NULL,
  dia_semana TEXT NOT NULL
);

CREATE TABLE dim_sucursal (
  sucursal_id INTEGER PRIMARY KEY,         -- 0 = SIN ASIGNAR
  nombre      TEXT NOT NULL UNIQUE
);

CREATE TABLE dim_producto (
  producto_id INTEGER PRIMARY KEY,
  nombre      TEXT NOT NULL UNIQUE,
  categoria   TEXT NOT NULL
);

CREATE TABLE fact_ventas (
  venta_id          INTEGER PRIMARY KEY AUTOINCREMENT,
  id_venta_origen   TEXT NOT NULL,
  fuente            TEXT NOT NULL DEFAULT 'ERP',
  fila_origen       INTEGER,
  fecha_id          INTEGER NOT NULL REFERENCES dim_fecha(fecha_id),
  sucursal_id       INTEGER NOT NULL REFERENCES dim_sucursal(sucursal_id),
  sucursal_original TEXT,                  -- texto tal como llegó
  producto_id       INTEGER NOT NULL REFERENCES dim_producto(producto_id),
  cantidad          INTEGER NOT NULL,
  precio_unitario   NUMERIC(10,2) NOT NULL,
  descuento         NUMERIC(10,2) NOT NULL DEFAULT 0,
  venta_neta        NUMERIC(10,2) NOT NULL,
  estado            TEXT NOT NULL CHECK (estado IN
                    ('ACEPTADO','CORREGIDO','EXCLUIDO_PROVISIONAL','PENDIENTE')),
  motivo            TEXT,
  UNIQUE (id_venta_origen, fuente)         -- evita contar una venta dos veces
);

CREATE TABLE fact_meta (
  sucursal_id  INTEGER NOT NULL REFERENCES dim_sucursal(sucursal_id),
  anio         INTEGER NOT NULL,
  mes          INTEGER NOT NULL,
  meta_mensual NUMERIC(12,2) NOT NULL,
  PRIMARY KEY (sucursal_id, anio, mes)
);

CREATE TABLE incidencias (
  incidencia_id   INTEGER PRIMARY KEY AUTOINCREMENT,
  id_venta        TEXT,
  fila_origen     INTEGER,
  regla           TEXT,
  estado          TEXT,
  motivo          TEXT,
  venta_neta      NUMERIC(10,2),
  accion_sugerida TEXT,
  revision        TEXT DEFAULT 'ABIERTA'
);
