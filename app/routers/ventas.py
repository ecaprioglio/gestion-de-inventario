import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_db
from app.modelos import VentaCrear
from app.rbac import requiere
from app.registros import auditar

router = APIRouter(prefix="/ventas", tags=["ventas"])


@router.post("", status_code=201)
def registrar(datos: VentaCrear,
              usuario: dict = Depends(requiere("ventas:registrar")),
              db: sqlite3.Connection = Depends(get_db)):
    cliente_id = None
    if datos.cliente_codigo:
        c = db.execute("SELECT id FROM clientes WHERE codigo = ?",
                       (datos.cliente_codigo,)).fetchone()
        if c is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")
        cliente_id = c["id"]

    p = db.execute("SELECT precio_venta FROM productos WHERE id = ?",
                   (datos.producto_id,)).fetchone()
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")

    with db:
        # Se descuenta solo si alcanza el stock (evita sobreventa)
        cur = db.execute("UPDATE productos SET stock = stock - ? WHERE id = ? AND stock >= ?",
                         (datos.cantidad, datos.producto_id, datos.cantidad))
        if cur.rowcount == 0:
            raise HTTPException(status.HTTP_409_CONFLICT, "Stock insuficiente")
        cur = db.execute(
            """INSERT INTO ventas (producto_id, cliente_id, vendedor_id, cantidad,
               precio_unitario, metodo_pago) VALUES (?, ?, ?, ?, ?, ?)""",
            (datos.producto_id, cliente_id, usuario["id"], datos.cantidad,
             p["precio_venta"], datos.metodo_pago),
        )
        db.execute("INSERT INTO movimientos_stock (producto_id, usuario_id, tipo, cantidad) "
                   "VALUES (?, ?, 'venta', ?)",
                   (datos.producto_id, usuario["id"], -datos.cantidad))
    auditar(usuario["id"], "ventas:registrar", f"/ventas/{cur.lastrowid}", "permitido")
    return {"id": cur.lastrowid, "total": p["precio_venta"] * datos.cantidad}


@router.get("")
def listar(usuario: dict = Depends(requiere("ventas:ver_propias")),
           db: sqlite3.Connection = Depends(get_db)):
    consulta = """SELECT v.id, v.producto_id, c.codigo AS cliente_codigo, v.vendedor_id,
                  v.cantidad, v.precio_unitario, v.metodo_pago, v.fecha
                  FROM ventas v LEFT JOIN clientes c ON c.id = v.cliente_id"""
    # El vendedor solo ve sus ventas; el filtro lo pone el servidor.
    if "ventas:ver_todas" in usuario["permisos"]:
        filas = db.execute(consulta + " ORDER BY v.id").fetchall()
    else:
        filas = db.execute(consulta + " WHERE v.vendedor_id = ? ORDER BY v.id",
                           (usuario["id"],)).fetchall()
    return [dict(f) for f in filas]
