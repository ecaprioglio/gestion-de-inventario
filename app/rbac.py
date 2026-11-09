"""Control de acceso basado en roles (RBAC).

La matriz está en app/permisos.py. Cada endpoint declara qué permiso
necesita con `Depends(requiere("permiso"))`; la verificación se hace
siempre en el servidor, nunca se confía en el cliente.
"""
from fastapi import Depends, HTTPException, Request, status

from app.auth import usuario_actual
from app.permisos import PERMISOS
from app.registros import auditar


def requiere(permiso: str):
    """Dependencia de FastAPI: deja pasar solo si el rol tiene el permiso.
    Los rechazos quedan en auditoría."""
    if permiso not in PERMISOS:
        raise ValueError(f"Permiso desconocido: {permiso}")

    def verificar(request: Request, usuario: dict = Depends(usuario_actual)) -> dict:
        if permiso not in usuario["permisos"]:
            auditar(usuario["id"], permiso, request.url.path, "denegado")
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                "No tienes permiso para esta acción")
        return usuario

    return verificar
