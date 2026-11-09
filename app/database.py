"""Conexión a SQLite, creación del esquema y carga de roles/permisos."""
import os
import sqlite3
from pathlib import Path

from app import config, seguridad
from app.permisos import MATRIZ, PERMISOS, ROLES

SCHEMA = Path(__file__).with_name("schema.sql")


def conectar() -> sqlite3.Connection:
    con = sqlite3.connect(config.ruta_db())
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def get_db():
    """Dependencia de FastAPI: una conexión por petición."""
    con = conectar()
    try:
        yield con
    finally:
        con.close()


def init_db() -> None:
    con = conectar()
    with con:
        con.executescript(SCHEMA.read_text(encoding="utf-8"))
        _cargar_rbac(con)
        _crear_admin_inicial(con)
    con.close()


def _cargar_rbac(con: sqlite3.Connection) -> None:
    for nombre, desc in ROLES.items():
        con.execute("INSERT OR IGNORE INTO roles (nombre, descripcion) VALUES (?, ?)",
                    (nombre, desc))
    for codigo, desc in PERMISOS.items():
        con.execute("INSERT OR IGNORE INTO permisos (codigo, descripcion) VALUES (?, ?)",
                    (codigo, desc))
    # Se reconstruye la relación para que la BD refleje exactamente la matriz
    con.execute("DELETE FROM rol_permisos")
    for rol, permisos in MATRIZ.items():
        for p in permisos:
            con.execute(
                """INSERT INTO rol_permisos (rol_id, permiso_id)
                   SELECT r.id, p.id FROM roles r, permisos p
                   WHERE r.nombre = ? AND p.codigo = ?""",
                (rol, p),
            )


def _crear_admin_inicial(con: sqlite3.Connection) -> None:
    """Crea el primer administrador solo si no hay usuarios y vienen las
    variables APP_ADMIN_*. Así no existe un admin con clave por defecto."""
    hay_usuarios = con.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
    usuario = os.environ.get("APP_ADMIN_USER")
    email = os.environ.get("APP_ADMIN_EMAIL")
    password = os.environ.get("APP_ADMIN_PASSWORD")
    if hay_usuarios or not (usuario and email and password):
        return
    con.execute(
        """INSERT INTO usuarios (username, email, password_hash, rol_id)
           VALUES (?, ?, ?, (SELECT id FROM roles WHERE nombre = 'administrador'))""",
        (usuario, email.lower(), seguridad.hash_password(password)),
    )


def permisos_de_rol(con: sqlite3.Connection, rol_id: int) -> set[str]:
    filas = con.execute(
        """SELECT p.codigo FROM rol_permisos rp
           JOIN permisos p ON p.id = rp.permiso_id
           WHERE rp.rol_id = ?""",
        (rol_id,),
    ).fetchall()
    return {f["codigo"] for f in filas}
