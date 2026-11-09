import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from app import seguridad
from app.database import get_db, permisos_de_rol
from app.modelos import CambioRol, UsuarioCrear
from app.rbac import requiere
from app.registros import auditar

router = APIRouter(tags=["usuarios y roles"])


@router.post("/usuarios", status_code=201)
def crear_usuario(datos: UsuarioCrear,
                  admin: dict = Depends(requiere("usuarios:gestionar")),
                  db: sqlite3.Connection = Depends(get_db)):
    try:
        with db:
            cur = db.execute(
                """INSERT INTO usuarios (username, email, nombre_visible, password_hash, rol_id)
                   VALUES (?, ?, ?, ?, (SELECT id FROM roles WHERE nombre = ?))""",
                (datos.username, datos.email.lower(), datos.nombre_visible,
                 seguridad.hash_password(datos.password), datos.rol),
            )
    except sqlite3.IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, "El usuario o email ya existe")
    auditar(admin["id"], "usuarios:crear", f"/usuarios/{cur.lastrowid}", "permitido")
    return {"id": cur.lastrowid, "username": datos.username, "rol": datos.rol}


@router.get("/usuarios")
def listar_usuarios(admin: dict = Depends(requiere("usuarios:gestionar")),
                    db: sqlite3.Connection = Depends(get_db)):
    filas = db.execute(
        """SELECT u.id, u.username, u.email, r.nombre AS rol, u.activo
           FROM usuarios u JOIN roles r ON r.id = u.rol_id ORDER BY u.id"""
    ).fetchall()
    # Incluso el admin ve el email enmascarado en el listado
    return [{**dict(f), "email": seguridad.enmascarar_email(f["email"])} for f in filas]


@router.put("/usuarios/{usuario_id}/rol")
def cambiar_rol(usuario_id: int, datos: CambioRol,
                admin: dict = Depends(requiere("roles:gestionar")),
                db: sqlite3.Connection = Depends(get_db)):
    if usuario_id == admin["id"]:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "No puedes cambiar tu propio rol")
    with db:
        cur = db.execute("UPDATE usuarios SET rol_id = (SELECT id FROM roles WHERE nombre = ?) "
                         "WHERE id = ?", (datos.rol, usuario_id))
    if cur.rowcount == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
    auditar(admin["id"], "roles:cambiar", f"/usuarios/{usuario_id}/rol", "permitido")
    return {"id": usuario_id, "rol": datos.rol}


@router.delete("/usuarios/{usuario_id}", status_code=204)
def desactivar_usuario(usuario_id: int,
                       admin: dict = Depends(requiere("usuarios:gestionar")),
                       db: sqlite3.Connection = Depends(get_db)):
    if usuario_id == admin["id"]:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No puedes desactivarte a ti mismo")
    with db:
        cur = db.execute("UPDATE usuarios SET activo = 0 WHERE id = ?", (usuario_id,))
        db.execute("DELETE FROM sesiones WHERE usuario_id = ?", (usuario_id,))
    if cur.rowcount == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
    auditar(admin["id"], "usuarios:desactivar", f"/usuarios/{usuario_id}", "permitido")


@router.get("/roles")
def listar_roles(admin: dict = Depends(requiere("roles:gestionar")),
                 db: sqlite3.Connection = Depends(get_db)):
    roles = db.execute("SELECT id, nombre, descripcion FROM roles ORDER BY id").fetchall()
    return [{**dict(r), "permisos": sorted(permisos_de_rol(db, r["id"]))} for r in roles]
