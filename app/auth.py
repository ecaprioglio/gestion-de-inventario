"""Autenticación: obtiene el usuario a partir del token Bearer."""
import sqlite3
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app import seguridad
from app.database import get_db, permisos_de_rol

_bearer = HTTPBearer(auto_error=False)

NO_AUTENTICADO = HTTPException(
    status.HTTP_401_UNAUTHORIZED,
    "No autenticado o sesión expirada",
    headers={"WWW-Authenticate": "Bearer"},
)


def ahora() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def usuario_actual(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: sqlite3.Connection = Depends(get_db),
) -> dict:
    if cred is None:
        raise NO_AUTENTICADO
    fila = db.execute(
        """SELECT u.id, u.username, u.rol_id, r.nombre AS rol
           FROM sesiones s
           JOIN usuarios u ON u.id = s.usuario_id
           JOIN roles r ON r.id = u.rol_id
           WHERE s.token_hash = ? AND s.expira_en > ? AND u.activo = 1""",
        (seguridad.hash_token(cred.credentials), ahora()),
    ).fetchone()
    if fila is None:
        raise NO_AUTENTICADO
    usuario = dict(fila)
    # Los permisos se leen de la BD en cada petición: si un admin cambia el
    # rol de alguien, el cambio aplica de inmediato.
    usuario["permisos"] = permisos_de_rol(db, fila["rol_id"])
    usuario["token_hash"] = seguridad.hash_token(cred.credentials)
    return usuario
