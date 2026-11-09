import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from app import seguridad
from app.database import get_db
from app.modelos import ProveedorCrear
from app.rbac import requiere
from app.registros import auditar

router = APIRouter(prefix="/proveedores", tags=["proveedores"])


@router.post("", status_code=201)
def crear(datos: ProveedorCrear,
          usuario: dict = Depends(requiere("proveedores:gestionar")),
          db: sqlite3.Connection = Depends(get_db)):
    try:
        with db:
            cur = db.execute(
                """INSERT INTO proveedores (razon_social, rut_empresa, contacto_email_cifrado,
                   contacto_telefono_cifrado) VALUES (?, ?, ?, ?)""",
                (datos.razon_social, datos.rut_empresa.upper(),
                 seguridad.cifrar(datos.contacto_email.lower()),
                 seguridad.cifrar(datos.contacto_telefono)),
            )
    except sqlite3.IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, "El proveedor ya existe")
    auditar(usuario["id"], "proveedores:crear", f"/proveedores/{cur.lastrowid}", "permitido")
    return {"id": cur.lastrowid, "razon_social": datos.razon_social}


@router.get("")
def listar(usuario: dict = Depends(requiere("proveedores:leer")),
           db: sqlite3.Connection = Depends(get_db)):
    filas = db.execute("SELECT * FROM proveedores ORDER BY id").fetchall()
    resultado = []
    for f in filas:
        tel = seguridad.descifrar(f["contacto_telefono_cifrado"])
        resultado.append({
            "id": f["id"],
            "razon_social": f["razon_social"],
            "rut_empresa": f["rut_empresa"],
            # En el listado el contacto va enmascarado
            "contacto_email": seguridad.enmascarar_email(
                seguridad.descifrar(f["contacto_email_cifrado"])),
            "contacto_telefono": seguridad.enmascarar_telefono(tel) if tel else None,
        })
    return resultado


@router.get("/{proveedor_id}/contacto")
def ver_contacto(proveedor_id: int,
                 usuario: dict = Depends(requiere("proveedores:ver_contacto")),
                 db: sqlite3.Connection = Depends(get_db)):
    f = db.execute("SELECT * FROM proveedores WHERE id = ?", (proveedor_id,)).fetchone()
    if f is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proveedor no encontrado")
    auditar(usuario["id"], "proveedores:ver_contacto", f"/proveedores/{proveedor_id}",
            "permitido")
    return {"id": f["id"],
            "contacto_email": seguridad.descifrar(f["contacto_email_cifrado"]),
            "contacto_telefono": seguridad.descifrar(f["contacto_telefono_cifrado"])}
