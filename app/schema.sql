-- =====================================================================
-- ESQUEMA REDISEÑADO (versión 2)
-- Aplica minimización de datos, cifrado de campos sensibles,
-- seudonimización de clientes y RBAC almacenado en la base de datos.
-- =====================================================================

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
-- RBAC: roles, permisos y su relación
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS roles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre      TEXT NOT NULL UNIQUE
                CHECK (nombre IN ('administrador', 'encargado', 'vendedor')),
    descripcion TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS permisos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo      TEXT NOT NULL UNIQUE,      -- ej: 'productos:crear'
    descripcion TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rol_permisos (
    rol_id     INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permiso_id INTEGER NOT NULL REFERENCES permisos(id) ON DELETE CASCADE,
    PRIMARY KEY (rol_id, permiso_id)
);

-- ---------------------------------------------------------------------
-- Usuarios del sistema (personal del negocio). Solo lo necesario para
-- autenticarse y operar: sin RUT, dirección, fecha de nacimiento ni género.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS usuarios (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    username          TEXT NOT NULL UNIQUE CHECK (length(username) BETWEEN 3 AND 30),
    email             TEXT NOT NULL UNIQUE,          -- recuperación de cuenta
    nombre_visible    TEXT,                          -- opcional (ej: "Ángel L.")
    password_hash     TEXT NOT NULL,                 -- scrypt + sal, nunca texto plano
    rol_id            INTEGER NOT NULL REFERENCES roles(id),
    activo            INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
    intentos_fallidos INTEGER NOT NULL DEFAULT 0,
    bloqueado_hasta   TEXT,
    creado_en         TEXT NOT NULL DEFAULT (date('now'))  -- solo fecha, no hora
);

-- Sesiones: se guarda el HASH del token, no el token.
CREATE TABLE IF NOT EXISTS sesiones (
    token_hash TEXT PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    expira_en  TEXT NOT NULL
);

-- ---------------------------------------------------------------------
-- Proveedores: datos de empresa. El contacto personal se cifra.
-- Se elimina cuenta bancaria, RUT y nombre del contacto, dirección.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS proveedores (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    razon_social              TEXT NOT NULL,
    rut_empresa               TEXT NOT NULL UNIQUE,  -- dato de persona jurídica
    contacto_email_cifrado    TEXT NOT NULL,
    contacto_telefono_cifrado TEXT                   -- opcional
);

-- ---------------------------------------------------------------------
-- Productos (sin cambios de privacidad; precio_costo es dato comercial
-- reservado y se oculta a vendedores mediante la vista de abajo).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS productos (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    sku          TEXT NOT NULL UNIQUE,
    nombre       TEXT NOT NULL,
    marca        TEXT NOT NULL,
    categoria    TEXT NOT NULL CHECK (categoria IN ('calzado', 'ropa', 'accesorio')),
    talla        TEXT NOT NULL,
    color        TEXT NOT NULL,
    precio_costo INTEGER NOT NULL CHECK (precio_costo >= 0),
    precio_venta INTEGER NOT NULL CHECK (precio_venta > 0),
    stock        INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    proveedor_id INTEGER REFERENCES proveedores(id)
);

-- Vista sin costo ni proveedor: la usan los vendedores.
CREATE VIEW IF NOT EXISTS vista_productos_venta AS
    SELECT id, sku, nombre, marca, categoria, talla, color, precio_venta, stock
    FROM productos;

-- ---------------------------------------------------------------------
-- Clientes SEUDONIMIZADOS: la tabla operativa solo tiene un código.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS clientes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo        TEXT NOT NULL UNIQUE,      -- seudónimo, ej: CLI-8f3a2c91d0
    talla_calzado TEXT,                      -- opcional, para recomendar stock
    creado_en     TEXT NOT NULL DEFAULT (date('now'))
);

-- Tabla de re-identificación: vincula el seudónimo con la persona.
-- Datos cifrados; solo el rol administrador puede consultarla.
CREATE TABLE IF NOT EXISTS clientes_identidad (
    cliente_id     INTEGER PRIMARY KEY REFERENCES clientes(id) ON DELETE CASCADE,
    email_cifrado  TEXT NOT NULL,
    email_hmac     TEXT NOT NULL UNIQUE,     -- para buscar duplicados sin descifrar
    nombre_cifrado TEXT                      -- opcional
);

-- ---------------------------------------------------------------------
-- Ventas: sin número de tarjeta. Cliente opcional (venta anónima).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ventas (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id     INTEGER NOT NULL REFERENCES productos(id),
    cliente_id      INTEGER REFERENCES clientes(id),
    vendedor_id     INTEGER NOT NULL REFERENCES usuarios(id),
    cantidad        INTEGER NOT NULL CHECK (cantidad > 0),
    precio_unitario INTEGER NOT NULL CHECK (precio_unitario > 0),
    metodo_pago     TEXT NOT NULL
                    CHECK (metodo_pago IN ('efectivo', 'debito', 'credito', 'transferencia')),
    fecha           TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Movimientos de stock: sin IP del usuario.
CREATE TABLE IF NOT EXISTS movimientos_stock (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER NOT NULL REFERENCES productos(id),
    usuario_id  INTEGER NOT NULL REFERENCES usuarios(id),
    tipo        TEXT NOT NULL CHECK (tipo IN ('ingreso', 'venta', 'ajuste')),
    cantidad    INTEGER NOT NULL,
    fecha       TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ---------------------------------------------------------------------
-- Auditoría: quién (id), qué acción, sobre qué recurso y el resultado.
-- Nunca el cuerpo de la petición, ni contraseñas, ni tokens, ni emails.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS auditoria (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER,
    accion     TEXT NOT NULL,
    recurso    TEXT NOT NULL,
    resultado  TEXT NOT NULL CHECK (resultado IN ('permitido', 'denegado', 'error')),
    fecha      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- La auditoría es de solo inserción: no se puede modificar ni borrar.
CREATE TRIGGER IF NOT EXISTS auditoria_no_update
BEFORE UPDATE ON auditoria
BEGIN
    SELECT RAISE(ABORT, 'La auditoria no se puede modificar');
END;

CREATE TRIGGER IF NOT EXISTS auditoria_no_delete
BEFORE DELETE ON auditoria
BEGIN
    SELECT RAISE(ABORT, 'La auditoria no se puede borrar');
END;
