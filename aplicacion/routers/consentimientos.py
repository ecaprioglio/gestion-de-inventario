from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/consentimiento", tags=["Consentimiento"])

class ConsentimientoCreate(BaseModel):
    usuario_id: int
    finalidad: str
    version_texto: str

@router.post("")
def registrar_consentimiento(data: ConsentimientoCreate):
    return {"mensaje": "Consentimiento registrado con éxito", "estado": "otorgado", "fecha": datetime.now()}

@router.put("/revocar")
def revocar_consentimiento(usuario_id: int, finalidad: str):
    return {"mensaje": "Consentimiento revocado correctamente", "estado": "revocado", "fecha_revocacion": datetime.now()}
