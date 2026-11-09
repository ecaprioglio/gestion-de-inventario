"""Carga datos FICTICIOS para desarrollo y pruebas.

Regla del equipo: en desarrollo y pruebas nunca se usan datos reales de
clientes ni proveedores. Este script genera personas inventadas con el
dominio reservado @ejemplo.cl.

Uso (desde la raíz del repo, con el .env cargado):
    python -m scripts.datos_prueba
"""
import random

from dotenv import load_dotenv

load_dotenv()

from app import seguridad  # noqa: E402
from app.database import conectar, init_db  # noqa: E402

USUARIOS = [
    ("bodega1", "bodega1@ejemplo.cl", "encargado"),
    ("vendedor1", "vendedor1@ejemplo.cl", "vendedor"),
    ("vendedor2", "vendedor2@ejemplo.cl", "vendedor"),
]
PRODUCTOS = [
    ("ZAP-001", "Zapatilla urbana", "Marca A", "calzado", "40", "blanco", 25000, 49990),
    ("ZAP-002", "Zapatilla running", "Marca B", "calzado", "42", "negro", 30000, 59990),
    ("POL-001", "Polerón básico", "Marca C", "ropa", "M", "gris", 9000, 19990),
    ("GOR-001", "Jockey", "Marca A", "accesorio", "U", "azul", 4000, 9990),
]


def main():
    init_db()
    con = conectar()
    with con:
        for username, email, rol in USUARIOS:
            con.execute(
                """INSERT OR IGNORE INTO usuarios (username, email, password_hash, rol_id)
                   VALUES (?, ?, ?, (SELECT id FROM roles WHERE nombre = ?))""",
                (username, email, seguridad.hash_password("ClaveDemo2026"), rol),
            )
        con.execute(
            """INSERT OR IGNORE INTO proveedores (razon_social, rut_empresa,
               contacto_email_cifrado, contacto_telefono_cifrado) VALUES (?, ?, ?, ?)""",
            ("Importadora Ficticia SpA", "76.123.456-7",
             seguridad.cifrar("contacto@ejemplo.cl"), seguridad.cifrar("+56900000000")),
        )
        for p in PRODUCTOS:
            con.execute(
                """INSERT OR IGNORE INTO productos (sku, nombre, marca, categoria, talla, color,
                   precio_costo, precio_venta, stock, proveedor_id) VALUES (?,?,?,?,?,?,?,?,50,1)""",
                p,
            )
        hay_clientes = con.execute("SELECT COUNT(*) FROM clientes").fetchone()[0]
        for i in range(0 if hay_clientes else 10):
            email = f"cliente{i}@ejemplo.cl"
            codigo = seguridad.nuevo_seudonimo()
            cur = con.execute("INSERT INTO clientes (codigo, talla_calzado) VALUES (?, ?)",
                              (codigo, random.choice(["38", "40", "42"])))
            con.execute(
                """INSERT OR IGNORE INTO clientes_identidad (cliente_id, email_cifrado, email_hmac)
                   VALUES (?, ?, ?)""",
                (cur.lastrowid, seguridad.cifrar(email), seguridad.huella(email)),
            )
    con.close()
    print("Datos ficticios cargados. Clave de los usuarios demo: ClaveDemo2026")


if __name__ == "__main__":
    main()
