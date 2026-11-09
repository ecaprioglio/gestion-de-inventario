"""Modelos de entrada con validaciones.

`extra="forbid"` hace que cualquier campo no declarado (rut,
fecha_nacimiento, numero_tarjeta, direccion...) sea rechazado con 422.
Así el sistema no puede recibir ni guardar datos que no necesita.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

EMAIL = r"^[\w\.\-+]+@[\w\-]+(\.[\w\-]+)+$"
RUT_EMPRESA = r"^\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]$"
TELEFONO = r"^\+?\d{8,12}$"
Rol = Literal["administrador", "encargado", "vendedor"]


class Estricto(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LoginIn(Estricto):
    username: str = Field(min_length=3, max_length=30)
    password: str = Field(min_length=1, max_length=128)


def _password_robusta(v: str) -> str:
    if not (any(c.isalpha() for c in v) and any(c.isdigit() for c in v)):
        raise ValueError("La contraseña debe tener letras y números")
    return v


class UsuarioCrear(Estricto):
    username: str = Field(min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_.]+$")
    email: str = Field(max_length=120, pattern=EMAIL)
    password: str = Field(min_length=10, max_length=128)
    rol: Rol
    nombre_visible: str | None = Field(default=None, max_length=40)

    _pw = field_validator("password")(_password_robusta)


class CambioRol(Estricto):
    rol: Rol


class CambioPassword(Estricto):
    actual: str = Field(min_length=1, max_length=128)
    nueva: str = Field(min_length=10, max_length=128)

    _pw = field_validator("nueva")(_password_robusta)


class ProductoCrear(Estricto):
    sku: str = Field(min_length=3, max_length=30)
    nombre: str = Field(min_length=2, max_length=80)
    marca: str = Field(min_length=1, max_length=40)
    categoria: Literal["calzado", "ropa", "accesorio"]
    talla: str = Field(min_length=1, max_length=10)
    color: str = Field(min_length=1, max_length=30)
    precio_costo: int = Field(ge=0)
    precio_venta: int = Field(gt=0)
    stock: int = Field(default=0, ge=0)
    proveedor_id: int | None = None


class ProductoEditar(Estricto):
    nombre: str | None = Field(default=None, min_length=2, max_length=80)
    precio_costo: int | None = Field(default=None, ge=0)
    precio_venta: int | None = Field(default=None, gt=0)
    talla: str | None = Field(default=None, max_length=10)
    color: str | None = Field(default=None, max_length=30)


class IngresoStock(Estricto):
    cantidad: int = Field(gt=0, le=10000)


class VentaCrear(Estricto):
    producto_id: int
    cantidad: int = Field(gt=0, le=100)
    metodo_pago: Literal["efectivo", "debito", "credito", "transferencia"]
    cliente_codigo: str | None = Field(default=None, pattern=r"^CLI-[0-9a-f]{10}$")


class ClienteCrear(Estricto):
    email: str = Field(max_length=120, pattern=EMAIL)   # para enviar la boleta
    nombre: str | None = Field(default=None, max_length=60)
    talla_calzado: str | None = Field(default=None, max_length=5)


class ProveedorCrear(Estricto):
    razon_social: str = Field(min_length=2, max_length=100)
    rut_empresa: str = Field(pattern=RUT_EMPRESA)
    contacto_email: str = Field(max_length=120, pattern=EMAIL)
    contacto_telefono: str | None = Field(default=None, pattern=TELEFONO)
