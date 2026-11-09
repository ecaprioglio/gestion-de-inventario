# gestion-de-inventario
Integrantes:
Estella Caprioglio
Krishna Salas
Ángel Larenas

Descripcion:
Permite gestionar a emprendimientos y negocios el stock disponible, registrar ingresos de nueva mercadería y actualizar inventario en tiempo real para ventas de moda y calzado.

Lenguaje y Framework: Python con FastAPI
Control de Versiones: GitHub
Gestión de Tareas: Trello
Comunicación y Colaboración: WhatsApp

## Objetivo del Equipo
Garantizar la entrega continua y automatizada de una API de gestión de inventario robusta, manteniendo estándares de calidad mediante integración continua y cobertura de pruebas automatizadas.

## Cierre de Riesgos de Shadow IT
Se confirma que no existen credenciales, claves API ni configuraciones críticas almacenadas en entornos locales no documentados o de acceso exclusivo de una sola persona. Todas las variables, dependencias e instrucciones del proyecto han sido centralizadas en este repositorio oficial y son accesibles por la totalidad del equipo.

## Seguridad y privacidad (Actividad 3)
- **Minimización de datos:** el esquema rediseñado (`app/schema.sql`) guarda solo lo necesario. El esquema original está en `docs/esquema_original.sql` como referencia. La API rechaza cualquier campo no declarado (RUT, fecha de nacimiento, tarjeta, etc.).
- **Protección de datos:** contraseñas con hash `scrypt` + sal; contactos de proveedores e identidad de clientes cifrados con Fernet; tokens de sesión guardados como hash.
- **Seudonimización:** los clientes se identifican con un código `CLI-xxxxxxxxxx`; la identidad real está cifrada en `clientes_identidad` y solo el administrador puede consultarla (queda auditado).
- **Anonimización:** reportes y exportaciones sin identificadores, con fecha por mes y supresión de grupos de menos de 3.
- **RBAC:** roles `administrador`, `encargado` y `vendedor`; matriz en `app/permisos.py`, verificada en el servidor en cada endpoint.
- **Registros:** la auditoría guarda solo id de usuario, acción, recurso y resultado, y no se puede modificar ni borrar. Los logs ocultan emails, RUT, tarjetas, tokens y contraseñas.

## Cómo ejecutar
```bash
pip install -r requirements.txt
cp .env.example .env          # completar las claves (ver instrucciones dentro)
python -m scripts.datos_prueba   # opcional: datos ficticios
uvicorn app.main:app --reload --env-file .env
```
Documentación interactiva: http://127.0.0.1:8000/docs

## Pruebas
```bash
pytest -v
```
Las pruebas crean una base de datos temporal y claves de prueba; no necesitan `.env`.
