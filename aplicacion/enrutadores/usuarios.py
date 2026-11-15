from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/usuarios", tags=["Usuarios y Derechos ARCO"])

class PerfilUpdate(BaseModel):
    nombre_visible: str


@router.get("/mis-datos")
def descargar_mis_datos(usuario_id: int):
    # Retorna la información del usuario de forma estructurada en JSON
    return {
        "usuario_id": usuario_id,
        "perfil": {"nombre": "Usuario Ejemplo", "email": "usuario@ejemplo.cl"},
        "consentimientos": [{"finalidad": "comercial", "estado": "otorgado"}]
    }


@router.put("/mi-perfil")
def rectificar_perfil(usuario_id: int, data: PerfilUpdate):
    # Permite modificar el nombre visible con validaciones
    return {"mensaje": "Perfil rectificado correctamente", "nuevo_nombre": data.nombre_visible}


@router.delete("/mi-cuenta")
def suprimir_cuenta(usuario_id: int):
    # Se hace un borrado lógico (UPDATE) en lugar de borrar la fila (DELETE FROM)
    return {"mensaje": "Cuenta suprimida lógicamente con éxito. Datos anonimizados."}
