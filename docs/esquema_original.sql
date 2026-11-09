-- =====================================================================
-- ESQUEMA ORIGINAL (versión 1) - SOLO COMO REFERENCIA PARA EL INFORME
-- Diseño inicial del sistema de Gestión de Inventario, antes de aplicar
-- minimización de datos, seudonimización y RBAC. NO se usa en la app.
-- =====================================================================

CREATE TABLE usuarios (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_completo     TEXT NOT NULL,
    rut                 TEXT NOT NULL,
    email               TEXT NOT NULL,
    telefono            TEXT NOT NULL,
    telefono_secundario TEXT,
    direccion           TEXT,
    fecha_nacimiento    TEXT,
    genero              TEXT,
    password            TEXT NOT NULL,        -- texto plano
    rol                 TEXT,                 -- texto libre: 'admin', 'Admin', 'vendedor'...
    fecha_registro      TEXT
);

CREATE TABLE proveedores (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    razon_social       TEXT NOT NULL,
    rut_empresa        TEXT,
    contacto_nombre    TEXT,
    contacto_rut       TEXT,
    contacto_telefono  TEXT,
    contacto_email     TEXT,
    cuenta_bancaria    TEXT,
    direccion          TEXT
);

CREATE TABLE productos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    sku           TEXT,
    nombre        TEXT NOT NULL,
    marca         TEXT,
    categoria     TEXT,
    talla         TEXT,
    color         TEXT,
    precio_costo  REAL,
    precio_venta  REAL,
    stock         INTEGER,
    proveedor_id  INTEGER REFERENCES proveedores(id)
);

CREATE TABLE clientes (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_completo  TEXT NOT NULL,
    rut              TEXT NOT NULL,
    email            TEXT,
    telefono         TEXT,
    direccion        TEXT,
    fecha_nacimiento TEXT,
    talla_calzado    TEXT,
    talla_ropa       TEXT
);

CREATE TABLE ventas (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id     INTEGER REFERENCES productos(id),
    cliente_id      INTEGER REFERENCES clientes(id),
    usuario_id      INTEGER REFERENCES usuarios(id),
    cantidad        INTEGER,
    precio_unitario REAL,
    metodo_pago     TEXT,
    numero_tarjeta  TEXT,
    fecha           TEXT
);

CREATE TABLE movimientos_stock (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER REFERENCES productos(id),
    usuario_id  INTEGER REFERENCES usuarios(id),
    tipo        TEXT,
    cantidad    INTEGER,
    ip_usuario  TEXT,
    fecha       TEXT
);

CREATE TABLE logs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_email TEXT,
    accion        TEXT,
    detalle       TEXT,          -- cuerpo completo de la petición (incluía contraseñas)
    ip            TEXT,
    fecha         TEXT
);
