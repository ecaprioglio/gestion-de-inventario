"""Clientes seudonimizados.

El vendedor registra al cliente y recibe solo un código (CLI-xxxx). Ventas,
reportes y logs usan ese código. La identidad real queda cifrada en
clientes_identidad y solo el administrador puede revertir el seudónimo.
"""
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from app import seguridad
from app.database import get_db
from app.modelos import ClienteCrear
from app.rbac import requiere
from app.registros import auditar

router = APIRouter(prefix="/clientes", tags=["clientes"])


@router.post("", status_code=201)
def registrar(datos: ClienteCrear,
              usuario: dict = Depends(requiere("clientes:crear")),
              db: sqlite3.Connection = Depends(get_db)):
    huella = seguridad.huella(datos.email)
    existente = db.execute(
        """SELECT c.codigo FROM clientes_identidad i JOIN clientes c ON c.id = i.cliente_id
           WHERE i.email_hmac = ?""", (huella,)).fetchone()
    if existente:
        return {"codigo": existente["codigo"], "nuevo": False}

    codigo = seguridad.nuevo_seudonimo()
    with db:
        cur = db.execute("INSERT INTO clientes (codigo, talla_calzado) VALUES (?, ?)",
                         (codigo, datos.talla_calzado))
        db.execute(
            """INSERT INTO clientes_identidad (cliente_id, email_cifrado, email_hmac,
               nombre_cifrado) VALUES (?, ?, ?, ?)""",
            (cur.lastrowid, seguridad.cifrar(datos.email.lower()), huella,
             seguridad.cifrar(datos.nombre)),
        )
    auditar(usuario["id"], "clientes:crear", f"/clientes/{codigo}", "permitido")
    return {"codigo": codigo, "nuevo": True}


@router.get("/{codigo}/identidad")
def reidentificar(codigo: str,
                  admin: dict = Depends(requiere("clientes:reidentificar")),
                  db: sqlite3.Connection = Depends(get_db)):
    fila = db.execute(
        """SELECT i.email_cifrado, i.nombre_cifrado FROM clientes c
           JOIN clientes_identidad i ON i.cliente_id = c.id WHERE c.codigo = ?""",
        (codigo,)).fetchone()
    if fila is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")
    # Cada re-identificación queda auditada
    auditar(admin["id"], "clientes:reidentificar", f"/clientes/{codigo}", "permitido")
    return {"codigo": codigo,
            "email": seguridad.descifrar(fila["email_cifrado"]),
            "nombre": seguridad.descifrar(fila["nombre_cifrado"])}
