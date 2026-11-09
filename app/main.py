"""API de Gestión de Inventario (moda y calzado)."""
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app import config
from app.database import init_db
from app.registros import log
from app.routers import auth, clientes, productos, proveedores, reportes, usuarios, ventas


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Si faltan las claves, la app no arranca (falla rápido y claro)
    config.clave_cifrado()
    config.clave_seudonimos()
    init_db()
    yield


produccion = os.environ.get("APP_ENV") == "produccion"
app = FastAPI(
    title="Gestión de Inventario",
    lifespan=lifespan,
    # En producción no se publica la documentación interactiva
    docs_url=None if produccion else "/docs",
    redoc_url=None,
    openapi_url=None if produccion else "/openapi.json",
)

for r in (auth, usuarios, productos, ventas, clientes, proveedores, reportes):
    app.include_router(r.router)


@app.exception_handler(RequestValidationError)
async def error_validacion(request: Request, exc: RequestValidationError):
    # FastAPI por defecto devuelve el valor recibido ("input"). Aquí solo se
    # indica el campo y el problema, para no repetir datos sensibles.
    errores = [{"campo": ".".join(str(x) for x in e["loc"][1:]), "error": e["msg"]}
               for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errores})


@app.exception_handler(Exception)
async def error_inesperado(request: Request, exc: Exception):
    # Al cliente: mensaje genérico + id. En el log: solo el tipo de error.
    error_id = uuid.uuid4().hex[:8]
    log.error("error_id=%s ruta=%s tipo=%s", error_id, request.url.path, type(exc).__name__)
    return JSONResponse(status_code=500,
                        content={"detail": "Error interno", "error_id": error_id})


@app.get("/")
def inicio():
    return {"sistema": "Gestión de Inventario", "estado": "ok"}
