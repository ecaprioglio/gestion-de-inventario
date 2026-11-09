"""Configuración leída desde variables de entorno.

Las claves criptográficas NUNCA se escriben en el código ni en la base de
datos: se entregan al proceso por variables de entorno (o un gestor de
secretos en producción). Si faltan, la aplicación no arranca.
"""
import os


class ConfigError(RuntimeError):
    pass


def _obligatoria(nombre: str) -> str:
    valor = os.environ.get(nombre)
    if not valor:
        raise ConfigError(
            f"Falta la variable de entorno {nombre}. "
            "Revisa .env.example para saber cómo generarla."
        )
    return valor


def ruta_db() -> str:
    return os.environ.get("APP_DB_PATH", "inventario.db")


def clave_cifrado() -> str:
    """Clave Fernet para cifrar campos sensibles (emails, teléfonos, nombres)."""
    return _obligatoria("APP_ENCRYPTION_KEY")


def clave_seudonimos() -> str:
    """Clave HMAC para calcular huellas de búsqueda (email_hmac)."""
    return _obligatoria("APP_PSEUDO_KEY")


# Duración de la sesión y política de bloqueo
MINUTOS_SESION = int(os.environ.get("APP_MINUTOS_SESION", "60"))
MAX_INTENTOS_LOGIN = 5
MINUTOS_BLOQUEO = 15
