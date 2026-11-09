import sqlite3
from collections import Counter, defaultdict

from fastapi import APIRouter, Depends

from app.anonimizacion import generalizar_fecha, suprimir_grupos_pequenos
from app.database import get_db
from app.rbac import requiere

router = APIRouter(tags=["reportes y auditoría"])


@router.get("/reportes/ventas")
def ventas_por_mes_y_categoria(usuario: dict = Depends(requiere("reportes:anonimos")),
                               db: sqlite3.Connection = Depends(get_db)):
    """Reporte anonimizado: sin vendedor, sin cliente y con fecha por mes."""
    filas = db.execute(
        """SELECT v.fecha, p.categoria, v.cantidad, v.precio_unitario
           FROM ventas v JOIN productos p ON p.id = v.producto_id"""
    ).fetchall()
    agregado = defaultdict(lambda: {"unidades": 0, "monto": 0})
    for f in filas:
        clave = (generalizar_fecha(f["fecha"]), f["categoria"])
        agregado[clave]["unidades"] += f["cantidad"]
        agregado[clave]["monto"] += f["cantidad"] * f["precio_unitario"]
    return [{"mes": mes, "categoria": cat, **valores}
            for (mes, cat), valores in sorted(agregado.items())]


@router.get("/reportes/clientes-por-talla")
def clientes_por_talla(usuario: dict = Depends(requiere("reportes:anonimos")),
                       db: sqlite3.Connection = Depends(get_db)):
    """Cuántos clientes hay por talla de calzado, con supresión de grupos
    pequeños para que no se pueda señalar a una persona."""
    tallas = Counter(
        f["talla_calzado"] or "sin dato"
        for f in db.execute("SELECT talla_calzado FROM clientes").fetchall()
    )
    return suprimir_grupos_pequenos(dict(sorted(tallas.items())))


@router.get("/auditoria")
def ver_auditoria(admin: dict = Depends(requiere("auditoria:leer")),
                  db: sqlite3.Connection = Depends(get_db)):
    filas = db.execute("SELECT * FROM auditoria ORDER BY id DESC LIMIT 200").fetchall()
    return [dict(f) for f in filas]
