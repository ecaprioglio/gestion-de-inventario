"""Registros (logs) y auditoría sin datos personales.

- `log`: logger de la aplicación. Un filtro reemplaza cualquier email, RUT,
  número de tarjeta, token o contraseña que se cuele en un mensaje.
- `auditar`: guarda en la tabla auditoria solo id de usuario, acción,
  recurso y resultado.
"""
import logging
import re

_PATRONES = [
    (re.compile(r"(?i)(password|contrase[nñ]a|token|authorization)\s*[=:]\s*\S+"),
     r"\1=[OCULTO]"),
    (re.compile(r"(?i)bearer\s+[A-Za-z0-9_\-\.]+"), "Bearer [OCULTO]"),
    (re.compile(r"[\w\.\-+]+@[\w\-]+\.[\w\.\-]+"), "[EMAIL]"),
    (re.compile(r"\b\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]\b"), "[RUT]"),
    (re.compile(r"\b(?:\d[ -]?){13,19}\b"), "[TARJETA]"),
]


def limpiar(texto: str) -> str:
    for patron, reemplazo in _PATRONES:
        texto = patron.sub(reemplazo, texto)
    return texto


class FiltroDatosSensibles(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = limpiar(record.getMessage())
        record.args = ()
        return True


log = logging.getLogger("inventario")
if not log.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(_h)
log.addFilter(FiltroDatosSensibles())
log.setLevel(logging.INFO)


def auditar(usuario_id: int | None, accion: str, recurso: str, resultado: str) -> None:
    # Import local para evitar import circular con database.py
    from app.database import conectar
    con = conectar()
    try:
        with con:
            con.execute(
                "INSERT INTO auditoria (usuario_id, accion, recurso, resultado) "
                "VALUES (?, ?, ?, ?)",
                (usuario_id, accion, limpiar(recurso), resultado),
            )
    finally:
        con.close()
    log.info("auditoria usuario=%s accion=%s recurso=%s resultado=%s",
             usuario_id, accion, recurso, resultado)

