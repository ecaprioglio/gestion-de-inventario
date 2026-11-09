"""Pruebas de seudonimización (clientes) y anonimización (reportes/exportación)."""
import re


def _registrar(client, tokens, email, talla="40", nombre=None):
    cuerpo = {"email": email, "talla_calzado": talla}
    if nombre:
        cuerpo["nombre"] = nombre
    r = client.post("/clientes", headers=tokens["vendedor"], json=cuerpo)
    assert r.status_code in (200, 201), r.text
    return r.json()["codigo"]


def test_cliente_recibe_solo_un_codigo(client, tokens, db):
    codigo = _registrar(client, tokens, "ana@ejemplo.cl", nombre="Ana Pérez")
    assert re.fullmatch(r"CLI-[0-9a-f]{10}", codigo)
    operativa = dict(db.execute("SELECT * FROM clientes").fetchone())
    assert set(operativa) == {"id", "codigo", "talla_calzado", "creado_en"}


def test_identidad_queda_cifrada(client, tokens, db):
    _registrar(client, tokens, "ana@ejemplo.cl", nombre="Ana Pérez")
    fila = str(dict(db.execute("SELECT * FROM clientes_identidad").fetchone()))
    assert "ana@ejemplo.cl" not in fila and "Ana Pérez" not in fila


def test_mismo_email_mismo_codigo(client, tokens, db):
    a = _registrar(client, tokens, "ana@ejemplo.cl")
    b = _registrar(client, tokens, "ANA@ejemplo.cl ")
    assert a == b
    assert db.execute("SELECT COUNT(*) FROM clientes").fetchone()[0] == 1


def test_codigo_no_se_deriva_del_email(client, tokens, db):
    codigo = _registrar(client, tokens, "ana@ejemplo.cl")
    huella = db.execute("SELECT email_hmac FROM clientes_identidad").fetchone()[0]
    assert codigo[4:] not in huella


def test_solo_admin_puede_reidentificar(client, tokens):
    codigo = _registrar(client, tokens, "ana@ejemplo.cl", nombre="Ana Pérez")
    for rol in ("vendedor", "encargado"):
        assert client.get(f"/clientes/{codigo}/identidad", headers=tokens[rol]).status_code == 403
    r = client.get(f"/clientes/{codigo}/identidad", headers=tokens["administrador"])
    assert r.status_code == 200
    assert r.json() == {"codigo": codigo, "email": "ana@ejemplo.cl", "nombre": "Ana Pérez"}


def test_reidentificacion_queda_auditada(client, tokens, db):
    codigo = _registrar(client, tokens, "ana@ejemplo.cl")
    client.get(f"/clientes/{codigo}/identidad", headers=tokens["administrador"])
    client.get(f"/clientes/{codigo}/identidad", headers=tokens["vendedor"])
    filas = db.execute("SELECT usuario_id, resultado FROM auditoria "
                       "WHERE accion = 'clientes:reidentificar' ORDER BY id").fetchall()
    assert [tuple(f) for f in filas] == [(1, "permitido"), (3, "denegado")]


def test_venta_usa_codigo_de_cliente(client, tokens, producto):
    codigo = _registrar(client, tokens, "ana@ejemplo.cl")
    client.post("/ventas", headers=tokens["vendedor"], json={
        "producto_id": producto, "cantidad": 1, "metodo_pago": "debito",
        "cliente_codigo": codigo})
    venta = client.get("/ventas", headers=tokens["vendedor"]).json()[0]
    assert venta["cliente_codigo"] == codigo
    assert "ana@ejemplo.cl" not in str(venta)


def test_reporte_de_ventas_es_anonimo(client, tokens, producto):
    codigo = _registrar(client, tokens, "ana@ejemplo.cl")
    for _ in range(2):
        client.post("/ventas", headers=tokens["vendedor"], json={
            "producto_id": producto, "cantidad": 1, "metodo_pago": "debito",
            "cliente_codigo": codigo})
    reporte = client.get("/reportes/ventas", headers=tokens["encargado"]).json()
    assert reporte[0]["unidades"] == 2 and reporte[0]["monto"] == 2 * 49990
    assert set(reporte[0]) == {"mes", "categoria", "unidades", "monto"}
    assert re.fullmatch(r"\d{4}-\d{2}", reporte[0]["mes"])   # fecha generalizada


def test_reporte_por_talla_suprime_grupos_pequenos(client, tokens):
    for i in range(3):
        _registrar(client, tokens, f"c{i}@ejemplo.cl", talla="40")
    _registrar(client, tokens, "unico@ejemplo.cl", talla="46")
    reporte = client.get("/reportes/clientes-por-talla", headers=tokens["encargado"]).json()
    assert reporte["40"] == 3
    assert reporte["46"] == "menos de 3"


def test_exportacion_anonima(client, tokens, producto):
    import sqlite3

    from app.database import conectar
    from scripts.exportar_anonimo import filas_anonimas
    venta = {"producto_id": producto, "cantidad": 1, "metodo_pago": "efectivo"}
    for _ in range(3):
        client.post("/ventas", headers=tokens["vendedor"], json=venta)
    con = conectar()
    con.row_factory = sqlite3.Row
    filas = filas_anonimas(con)
    con.close()
    assert len(filas) == 1
    assert set(filas[0]) == {"mes", "categoria", "talla", "ventas", "unidades", "monto"}


def test_exportacion_omite_grupos_pequenos(client, tokens, producto):
    from app.database import conectar
    from scripts.exportar_anonimo import filas_anonimas
    client.post("/ventas", headers=tokens["vendedor"],
                json={"producto_id": producto, "cantidad": 1, "metodo_pago": "efectivo"})
    con = conectar()
    assert filas_anonimas(con) == []
    con.close()
