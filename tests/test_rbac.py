"""Pruebas de la matriz RBAC: accesos permitidos y denegados por rol."""
import pytest

PERMITIDO, DENEGADO = "permitido", "denegado"

# (método, ruta, cuerpo, administrador, encargado, vendedor)
CASOS = [
    ("GET", "/usuarios", None, PERMITIDO, DENEGADO, DENEGADO),
    ("GET", "/roles", None, PERMITIDO, DENEGADO, DENEGADO),
    ("PUT", "/usuarios/4/rol", {"rol": "vendedor"}, PERMITIDO, DENEGADO, DENEGADO),
    ("GET", "/auth/yo", None, PERMITIDO, PERMITIDO, PERMITIDO),
    ("GET", "/productos", None, PERMITIDO, PERMITIDO, PERMITIDO),
    ("POST", "/productos/{p}/ingresos", {"cantidad": 5}, PERMITIDO, PERMITIDO, DENEGADO),
    ("PATCH", "/productos/{p}", {"precio_venta": 45990}, PERMITIDO, PERMITIDO, DENEGADO),
    ("POST", "/ventas", {"producto_id": "{p}", "cantidad": 1, "metodo_pago": "debito"},
     PERMITIDO, DENEGADO, PERMITIDO),
    ("GET", "/ventas", None, PERMITIDO, DENEGADO, PERMITIDO),
    ("POST", "/clientes", {"email": "c@ejemplo.cl"}, PERMITIDO, DENEGADO, PERMITIDO),
    ("GET", "/proveedores", None, PERMITIDO, PERMITIDO, DENEGADO),
    ("GET", "/reportes/ventas", None, PERMITIDO, PERMITIDO, DENEGADO),
    ("GET", "/auditoria", None, PERMITIDO, DENEGADO, DENEGADO),
    ("DELETE", "/productos/{p}", None, PERMITIDO, DENEGADO, DENEGADO),
]


def _sustituir(valor, p):
    if isinstance(valor, str):
        return int(p) if valor == "{p}" else valor.replace("{p}", str(p))
    if isinstance(valor, dict):
        return {k: _sustituir(v, p) for k, v in valor.items()}
    return valor


@pytest.mark.parametrize("rol_idx,rol", [(3, "administrador"), (4, "encargado"), (5, "vendedor")])
@pytest.mark.parametrize("caso", CASOS, ids=[f"{c[0]} {c[1]}" for c in CASOS])
def test_matriz_de_permisos(client, tokens, producto, caso, rol_idx, rol):
    metodo, ruta, cuerpo, esperado = caso[0], caso[1], caso[2], caso[rol_idx]
    r = client.request(metodo, _sustituir(ruta, producto), headers=tokens[rol],
                       json=_sustituir(cuerpo, producto))
    if esperado == DENEGADO:
        assert r.status_code == 403, f"{rol} debería ser rechazado en {metodo} {ruta}"
    else:
        assert r.status_code < 400, f"{rol} debería poder {metodo} {ruta}: {r.text}"


def test_vendedor_no_ve_precio_costo(client, tokens, producto):
    vendedor = client.get("/productos", headers=tokens["vendedor"]).json()[0]
    encargado = client.get("/productos", headers=tokens["encargado"]).json()[0]
    assert "precio_costo" not in vendedor and "proveedor_id" not in vendedor
    assert encargado["precio_costo"] == 25000


def test_vendedor_solo_ve_sus_ventas(client, tokens, producto):
    venta = {"producto_id": producto, "cantidad": 1, "metodo_pago": "efectivo"}
    client.post("/ventas", headers=tokens["vendedor"], json=venta)
    client.post("/ventas", headers=tokens["vendedor2"], json=venta)
    propias = client.get("/ventas", headers=tokens["vendedor"]).json()
    todas = client.get("/ventas", headers=tokens["administrador"]).json()
    assert len(propias) == 1 and len(todas) == 2


def test_rechazos_quedan_en_auditoria(client, tokens, db):
    client.get("/auditoria", headers=tokens["vendedor"])
    fila = db.execute("SELECT * FROM auditoria WHERE resultado = 'denegado' "
                      "AND accion = 'auditoria:leer'").fetchone()
    assert fila is not None


def test_cambio_de_rol_aplica_de_inmediato(client, tokens):
    # vendedor1 (id 3) pasa a encargado: con el MISMO token ya puede ver proveedores
    assert client.get("/proveedores", headers=tokens["vendedor"]).status_code == 403
    r = client.put("/usuarios/3/rol", headers=tokens["administrador"], json={"rol": "encargado"})
    assert r.status_code == 200
    assert client.get("/proveedores", headers=tokens["vendedor"]).status_code == 200


def test_admin_no_puede_cambiar_su_propio_rol(client, tokens):
    r = client.put("/usuarios/1/rol", headers=tokens["administrador"], json={"rol": "vendedor"})
    assert r.status_code == 400


def test_rol_inexistente_es_rechazado(client, tokens):
    r = client.put("/usuarios/3/rol", headers=tokens["administrador"], json={"rol": "superadmin"})
    assert r.status_code == 422


def test_usuario_desactivado_pierde_acceso(client, tokens):
    assert client.delete("/usuarios/3", headers=tokens["administrador"]).status_code == 204
    assert client.get("/productos", headers=tokens["vendedor"]).status_code == 401


def test_venta_sin_stock_es_rechazada(client, tokens, producto):
    r = client.post("/ventas", headers=tokens["vendedor"],
                    json={"producto_id": producto, "cantidad": 11, "metodo_pago": "debito"})
    assert r.status_code == 409


def test_ningun_endpoint_expone_claves(client, tokens, entorno):
    import os
    clave = os.environ["APP_ENCRYPTION_KEY"]
    for ruta in ["/", "/auth/yo", "/roles", "/usuarios", "/openapi.json"]:
        assert clave not in client.get(ruta, headers=tokens["administrador"]).text
