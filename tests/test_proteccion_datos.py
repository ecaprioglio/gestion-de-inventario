"""Pruebas de minimización de datos, cifrado, errores y registros."""
import logging
import sqlite3

import pytest

from tests.conftest import PRODUCTO

PROVEEDOR = {"razon_social": "Importadora Ficticia SpA", "rut_empresa": "76.123.456-7",
             "contacto_email": "contacto@ejemplo.cl", "contacto_telefono": "+56912345678"}


@pytest.mark.parametrize("campo,valor", [
    ("rut", "12.345.678-9"),
    ("fecha_nacimiento", "2000-01-01"),
    ("direccion", "Av. Siempre Viva 123"),
    ("genero", "no binario"),
    ("telefono_secundario", "+56911111111"),
])
def test_usuario_con_campos_innecesarios_es_rechazado(client, tokens, campo, valor):
    r = client.post("/usuarios", headers=tokens["administrador"], json={
        "username": "nuevo", "email": "nuevo@ejemplo.cl", "password": "ClaveSegura2026",
        "rol": "vendedor", campo: valor})
    assert r.status_code == 422
    assert valor not in r.text          # el error no repite el dato enviado


def test_venta_con_numero_de_tarjeta_es_rechazada(client, tokens, producto, db):
    r = client.post("/ventas", headers=tokens["vendedor"], json={
        "producto_id": producto, "cantidad": 1, "metodo_pago": "credito",
        "numero_tarjeta": "4111111111111111"})
    assert r.status_code == 422
    assert "4111111111111111" not in r.text
    assert db.execute("SELECT COUNT(*) FROM ventas").fetchone()[0] == 0


def test_cliente_con_rut_es_rechazado(client, tokens):
    r = client.post("/clientes", headers=tokens["vendedor"],
                    json={"email": "c@ejemplo.cl", "rut": "12.345.678-9"})
    assert r.status_code == 422


def test_contacto_proveedor_se_guarda_cifrado(client, tokens, db):
    assert client.post("/proveedores", headers=tokens["encargado"], json=PROVEEDOR).status_code == 201
    fila = dict(db.execute("SELECT * FROM proveedores").fetchone())
    assert "contacto@ejemplo.cl" not in str(fila)
    assert "+56912345678" not in str(fila)


def test_listado_de_proveedores_enmascara_contacto(client, tokens):
    client.post("/proveedores", headers=tokens["encargado"], json=PROVEEDOR)
    p = client.get("/proveedores", headers=tokens["encargado"]).json()[0]
    assert p["contacto_email"] == "c***@ejemplo.cl"
    assert p["contacto_telefono"].endswith("5678") and p["contacto_telefono"].startswith("*")


def test_contacto_completo_solo_con_permiso_y_auditado(client, tokens, db):
    client.post("/proveedores", headers=tokens["encargado"], json=PROVEEDOR)
    assert client.get("/proveedores/1/contacto", headers=tokens["vendedor"]).status_code == 403
    r = client.get("/proveedores/1/contacto", headers=tokens["encargado"])
    assert r.json()["contacto_email"] == "contacto@ejemplo.cl"
    assert db.execute("SELECT COUNT(*) FROM auditoria WHERE accion = 'proveedores:ver_contacto' "
                      "AND resultado = 'permitido'").fetchone()[0] == 1


def test_listado_usuarios_enmascara_email(client, tokens):
    usuarios = client.get("/usuarios", headers=tokens["administrador"]).json()
    assert all("***@" in u["email"] for u in usuarios)
    assert all("password_hash" not in u for u in usuarios)


def test_auditoria_no_guarda_datos_sensibles(client, tokens, producto, db):
    client.post("/clientes", headers=tokens["vendedor"], json={"email": "secreto@ejemplo.cl"})
    texto = str([dict(f) for f in db.execute("SELECT * FROM auditoria")])
    assert "secreto@ejemplo.cl" not in texto
    assert "ClaveDemo2026" not in texto


def test_auditoria_no_se_puede_modificar_ni_borrar(client, tokens, db):
    with pytest.raises(sqlite3.DatabaseError):
        db.execute("UPDATE auditoria SET resultado = 'permitido'")
    with pytest.raises(sqlite3.DatabaseError):
        db.execute("DELETE FROM auditoria")


def test_bd_rechaza_stock_negativo(client, tokens, producto, db):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("UPDATE productos SET stock = -1")


def test_bd_rechaza_metodo_de_pago_invalido(client, tokens, producto, db):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO ventas (producto_id, vendedor_id, cantidad, precio_unitario, "
                   "metodo_pago) VALUES (1, 1, 1, 1000, 'tarjeta 4111111111111111')")


def test_filtro_de_logs_oculta_datos_sensibles():
    from app.registros import limpiar
    texto = limpiar("login juan@correo.cl password=Hola123 rut 12.345.678-9 "
                    "tarjeta 4111 1111 1111 1111 Bearer abc.def")
    for dato in ["juan@correo.cl", "Hola123", "12.345.678-9", "4111 1111", "abc.def"]:
        assert dato not in texto


def test_logs_de_la_app_no_muestran_emails(caplog):
    from app.registros import log
    with caplog.at_level(logging.INFO, logger="inventario"):
        log.info("usuario %s hizo algo", "juan@correo.cl")
    assert "juan@correo.cl" not in caplog.text


def test_error_interno_no_expone_detalles(client, tokens, monkeypatch):
    import app.routers.productos as rp

    def falla(*a, **k):
        raise RuntimeError("detalle interno con ruta /home/secreto y SQL")
    monkeypatch.setattr(rp, "auditar", falla)
    r = client.post("/productos", headers=tokens["encargado"], json={**PRODUCTO, "sku": "X-9"})
    assert r.status_code == 500
    assert r.json()["detail"] == "Error interno" and "secreto" not in r.text


def test_app_no_arranca_sin_claves(monkeypatch):
    from fastapi.testclient import TestClient

    from app.config import ConfigError
    from app.main import app
    monkeypatch.delenv("APP_ENCRYPTION_KEY")
    with pytest.raises(ConfigError):
        with TestClient(app):
            pass


def test_clave_de_cifrado_no_esta_en_la_bd(client, tokens, entorno):
    import os
    clave = os.environ["APP_ENCRYPTION_KEY"].encode()
    assert clave not in entorno.read_bytes()
