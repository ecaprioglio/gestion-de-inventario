"""Configuración común de las pruebas.

Cada prueba usa una base de datos nueva en una carpeta temporal y claves
generadas en el momento: nunca se usan datos ni claves reales.
"""
import secrets
import sqlite3

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

ADMIN = ("admin", "admin@ejemplo.cl", "AdminSegura2026")
CLAVE_DEMO = "ClaveDemo2026"


@pytest.fixture(autouse=True)
def entorno(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("APP_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("APP_PSEUDO_KEY", secrets.token_hex(32))
    monkeypatch.setenv("APP_ADMIN_USER", ADMIN[0])
    monkeypatch.setenv("APP_ADMIN_EMAIL", ADMIN[1])
    monkeypatch.setenv("APP_ADMIN_PASSWORD", ADMIN[2])
    return tmp_path / "test.db"


@pytest.fixture
def client():
    from app.main import app
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture
def db(entorno):
    """Conexión directa a la BD para comprobar qué quedó guardado."""
    con = sqlite3.connect(entorno)
    con.row_factory = sqlite3.Row
    yield con
    con.close()


def login(client, username, password):
    r = client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def tokens(client):
    """Crea un usuario por rol y devuelve sus cabeceras de autorización."""
    admin = login(client, ADMIN[0], ADMIN[2])
    for username, rol in [("bodega1", "encargado"), ("vendedor1", "vendedor"),
                          ("vendedor2", "vendedor")]:
        r = client.post("/usuarios", headers=admin, json={
            "username": username, "email": f"{username}@ejemplo.cl",
            "password": CLAVE_DEMO, "rol": rol})
        assert r.status_code == 201, r.text
    return {
        "administrador": admin,
        "encargado": login(client, "bodega1", CLAVE_DEMO),
        "vendedor": login(client, "vendedor1", CLAVE_DEMO),
        "vendedor2": login(client, "vendedor2", CLAVE_DEMO),
    }


PRODUCTO = {"sku": "ZAP-001", "nombre": "Zapatilla urbana", "marca": "Marca A",
            "categoria": "calzado", "talla": "40", "color": "blanco",
            "precio_costo": 25000, "precio_venta": 49990, "stock": 10}


@pytest.fixture
def producto(client, tokens):
    r = client.post("/productos", headers=tokens["encargado"], json=PRODUCTO)
    assert r.status_code == 201, r.text
    return r.json()["id"]
