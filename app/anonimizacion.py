"""Técnicas de anonimización usadas en reportes y exportaciones.

- Eliminación de identificadores: no se incluyen ids de vendedor ni cliente.
- Generalización: la fecha y hora exacta pasa a "año-mes".
- Supresión de grupos pequeños (k-anonimato): si un grupo tiene menos de
  K personas, no se publica el número exacto, porque podría apuntar a
  alguien concreto.
"""
K_MINIMO = 3


def generalizar_fecha(fecha: str) -> str:
    """'2026-11-08 21:50:13' -> '2026-11'"""
    return fecha[:7]


def suprimir_grupos_pequenos(grupos: dict[str, int], k: int = K_MINIMO) -> dict[str, int | str]:
    return {clave: (n if n >= k else f"menos de {k}") for clave, n in grupos.items()}
