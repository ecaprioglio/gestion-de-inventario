"""Funciones de seguridad: contraseñas, cifrado, seudónimos y tokens."""
import base64
import hashlib
import hmac
import secrets

from cryptography.fernet import Fernet, InvalidToken

from app import config

# ---------------------------------------------------------------------
# Contraseñas: scrypt con sal aleatoria (librería estándar de Python)
# Formato guardado: scrypt$n$r$p$sal_b64$hash_b64
# ---------------------------------------------------------------------
_N, _R, _P = 2**14, 8, 1


def hash_password(password: str) -> str:
    sal = secrets.token_bytes(16)
    h = hashlib.scrypt(password.encode(), salt=sal, n=_N, r=_R, p=_P, dklen=32)
    return "scrypt${}${}${}${}${}".format(
        _N, _R, _P,
        base64.b64encode(sal).decode(),
        base64.b64encode(h).decode(),
    )


def verificar_password(password: str, guardado: str) -> bool:
    try:
        _, n, r, p, sal_b64, hash_b64 = guardado.split("$")
        sal = base64.b64decode(sal_b64)
        esperado = base64.b64decode(hash_b64)
        h = hashlib.scrypt(password.encode(), salt=sal, n=int(n), r=int(r),
                           p=int(p), dklen=len(esperado))
    except (ValueError, TypeError):
        return False
    # compare_digest evita ataques de tiempo
    return hmac.compare_digest(h, esperado)


# Hash falso para que el login tarde lo mismo aunque el usuario no exista
HASH_FALSO = hash_password(secrets.token_hex(16))


# ---------------------------------------------------------------------
# Cifrado simétrico de campos sensibles (Fernet = AES-128-CBC + HMAC)
# ---------------------------------------------------------------------
def _fernet() -> Fernet:
    return Fernet(config.clave_cifrado().encode())


def cifrar(texto: str | None) -> str | None:
    if texto is None:
        return None
    return _fernet().encrypt(texto.encode()).decode()


def descifrar(token: str | None) -> str | None:
    if token is None:
        return None
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        # No se revela el motivo: solo que no se pudo descifrar
        raise ValueError("No se pudo descifrar el dato")


# ---------------------------------------------------------------------
# Seudonimización
# ---------------------------------------------------------------------
def huella(texto: str) -> str:
    """HMAC-SHA256 con clave secreta. Permite buscar un email sin guardarlo
    en claro. Sin la clave no se puede recalcular (a diferencia de un hash
    simple, que se rompe probando emails conocidos)."""
    normalizado = texto.strip().lower().encode()
    return hmac.new(config.clave_seudonimos().encode(), normalizado,
                    hashlib.sha256).hexdigest()


def nuevo_seudonimo(prefijo: str = "CLI") -> str:
    """Código aleatorio: no se deriva de ningún dato de la persona."""
    return f"{prefijo}-{secrets.token_hex(5)}"


# ---------------------------------------------------------------------
# Tokens de sesión
# ---------------------------------------------------------------------
def nuevo_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# ---------------------------------------------------------------------
# Enmascarado para mostrar datos parcialmente
# ---------------------------------------------------------------------
def enmascarar_email(email: str) -> str:
    usuario, _, dominio = email.partition("@")
    return f"{usuario[:1]}***@{dominio}"


def enmascarar_telefono(telefono: str) -> str:
    return "*" * max(len(telefono) - 4, 0) + telefono[-4:]
