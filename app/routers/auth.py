import sqlite3
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app import config, seguridad
from app.auth import ahora, usuario_actual
from app.database import get_db
from app.modelos import CambioPassword, LoginIn
from app.rbac import requiere
from app.registros import auditar

router = APIRouter(prefix="/auth", tags=["autenticación"])

# Mismo mensaje si el usuario no existe o la clave es incorrecta:
# así no se puede averiguar qué usuarios existen.
CREDENCIALES_INVALIDAS = HTTPException(status.HTTP_401_UNAUTHORIZED,
                                       "Usuario o contraseña incorrectos")


def _en(minutos: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutos)).strftime(
        "%Y-%m-%d %H:%M:%S")


@router.post("/login")
def login(datos: LoginIn, db: sqlite3.Connection = Depends(get_db)):
    u = db.execute(
        "SELECT id, password_hash, activo, intentos_fallidos, bloqueado_hasta "
        "FROM usuarios WHERE username = ?",
        (datos.username,),
    ).fetchone()

    if u is None:
        seguridad.verificar_password(datos.password, seguridad.HASH_FALSO)
        auditar(None, "auth:login", "/auth/login", "denegado")
        raise CREDENCIALES_INVALIDAS

    if u["bloqueado_hasta"] and u["bloqueado_hasta"] > ahora():
        auditar(u["id"], "auth:login_bloqueado", "/auth/login", "denegado")
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            "Cuenta bloqueada temporalmente. Intenta más tarde.")

    if not u["activo"] or not seguridad.verificar_password(datos.password, u["password_hash"]):
        intentos = u["intentos_fallidos"] + 1
        bloqueo = _en(config.MINUTOS_BLOQUEO) if intentos >= config.MAX_INTENTOS_LOGIN else None
        with db:
            db.execute("UPDATE usuarios SET intentos_fallidos = ?, bloqueado_hasta = ? "
                       "WHERE id = ?", (0 if bloqueo else intentos, bloqueo, u["id"]))
        auditar(u["id"], "auth:login", "/auth/login", "denegado")
        raise CREDENCIALES_INVALIDAS

    token = seguridad.nuevo_token()
    with db:
        db.execute("UPDATE usuarios SET intentos_fallidos = 0, bloqueado_hasta = NULL "
                   "WHERE id = ?", (u["id"],))
        db.execute("DELETE FROM sesiones WHERE usuario_id = ? AND expira_en <= ?",
                   (u["id"], ahora()))
        db.execute("INSERT INTO sesiones (token_hash, usuario_id, expira_en) VALUES (?, ?, ?)",
                   (seguridad.hash_token(token), u["id"], _en(config.MINUTOS_SESION)))
    auditar(u["id"], "auth:login", "/auth/login", "permitido")
    return {"access_token": token, "token_type": "bearer",
            "expira_en_minutos": config.MINUTOS_SESION}


@router.post("/logout", status_code=204)
def logout(usuario: dict = Depends(usuario_actual), db: sqlite3.Connection = Depends(get_db)):
    with db:
        db.execute("DELETE FROM sesiones WHERE token_hash = ?", (usuario["token_hash"],))


@router.get("/yo")
def mis_datos(usuario: dict = Depends(requiere("perfil:ver_propio")),
              db: sqlite3.Connection = Depends(get_db)):
    u = db.execute("SELECT username, email, nombre_visible, creado_en FROM usuarios "
                   "WHERE id = ?", (usuario["id"],)).fetchone()
    return {**dict(u), "rol": usuario["rol"], "permisos": sorted(usuario["permisos"])}


@router.put("/yo/password", status_code=204)
def cambiar_password(datos: CambioPassword,
                     usuario: dict = Depends(requiere("perfil:ver_propio")),
                     db: sqlite3.Connection = Depends(get_db)):
    actual = db.execute("SELECT password_hash FROM usuarios WHERE id = ?",
                        (usuario["id"],)).fetchone()["password_hash"]
    if not seguridad.verificar_password(datos.actual, actual):
        raise CREDENCIALES_INVALIDAS
    with db:
        db.execute("UPDATE usuarios SET password_hash = ? WHERE id = ?",
                   (seguridad.hash_password(datos.nueva), usuario["id"]))
        # Se cierran las demás sesiones
        db.execute("DELETE FROM sesiones WHERE usuario_id = ? AND token_hash != ?",
                   (usuario["id"], usuario["token_hash"]))
    auditar(usuario["id"], "perfil:cambiar_password", "/auth/yo/password", "permitido")
