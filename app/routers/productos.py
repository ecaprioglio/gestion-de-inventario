import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_db
from app.modelos import IngresoStock, ProductoCrear, ProductoEditar
from app.rbac import requiere
from app.registros import auditar

router = APIRouter(prefix="/productos", tags=["productos"])


@router.get("")
def listar(usuario: dict = Depends(requiere("productos:leer")),
           db: sqlite3.Connection = Depends(get_db)):
    # Quien no tiene 'productos:ver_costo' consulta la VISTA, que no tiene
    # la columna precio_costo: el dato ni siquiera sale de la base de datos.
    if "productos:ver_costo" in usuario["permisos"]:
        filas = db.execute("SELECT * FROM productos ORDER BY id").fetchall()
    else:
        filas = db.execute("SELECT * FROM vista_productos_venta ORDER BY id").fetchall()
    return [dict(f) for f in filas]


@router.post("", status_code=201)
def crear(datos: ProductoCrear,
          usuario: dict = Depends(requiere("productos:crear")),
          db: sqlite3.Connection = Depends(get_db)):
    try:
        with db:
            cur = db.execute(
                """INSERT INTO productos (sku, nombre, marca, categoria, talla, color,
                   precio_costo, precio_venta, stock, proveedor_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (datos.sku, datos.nombre, datos.marca, datos.categoria, datos.talla,
                 datos.color, datos.precio_costo, datos.precio_venta, datos.stock,
                 datos.proveedor_id),
            )
    except sqlite3.IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, "SKU repetido o proveedor inexistente")
    auditar(usuario["id"], "productos:crear", f"/productos/{cur.lastrowid}", "permitido")
    return {"id": cur.lastrowid, **datos.model_dump()}


@router.patch("/{producto_id}")
def editar(producto_id: int, datos: ProductoEditar,
           usuario: dict = Depends(requiere("productos:editar")),
           db: sqlite3.Connection = Depends(get_db)):
    cambios = datos.model_dump(exclude_none=True)
    if not cambios:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No hay cambios")
    # Las columnas vienen del modelo (lista cerrada), no del usuario
    columnas = ", ".join(f"{c} = ?" for c in cambios)
    with db:
        cur = db.execute(f"UPDATE productos SET {columnas} WHERE id = ?",
                         (*cambios.values(), producto_id))
    if cur.rowcount == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    auditar(usuario["id"], "productos:editar", f"/productos/{producto_id}", "permitido")
    return {"id": producto_id, **cambios}


@router.delete("/{producto_id}", status_code=204)
def eliminar(producto_id: int,
             usuario: dict = Depends(requiere("productos:eliminar")),
             db: sqlite3.Connection = Depends(get_db)):
    try:
        with db:
            cur = db.execute("DELETE FROM productos WHERE id = ?", (producto_id,))
    except sqlite3.IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "El producto tiene ventas o movimientos asociados")
    if cur.rowcount == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    auditar(usuario["id"], "productos:eliminar", f"/productos/{producto_id}", "permitido")


@router.post("/{producto_id}/ingresos", status_code=201)
def ingresar_stock(producto_id: int, datos: IngresoStock,
                   usuario: dict = Depends(requiere("stock:ingresar")),
                   db: sqlite3.Connection = Depends(get_db)):
    with db:
        cur = db.execute("UPDATE productos SET stock = stock + ? WHERE id = ?",
                         (datos.cantidad, producto_id))
        if cur.rowcount == 0:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
        db.execute("INSERT INTO movimientos_stock (producto_id, usuario_id, tipo, cantidad) "
                   "VALUES (?, ?, 'ingreso', ?)", (producto_id, usuario["id"], datos.cantidad))
    stock = db.execute("SELECT stock FROM productos WHERE id = ?", (producto_id,)).fetchone()[0]
    auditar(usuario["id"], "stock:ingresar", f"/productos/{producto_id}/ingresos", "permitido")
    return {"producto_id": producto_id, "stock": stock}
