"""Matriz RBAC: roles, permisos y qué permisos tiene cada rol.

Es la fuente de verdad; al iniciar la app se copia a las tablas
roles / permisos / rol_permisos.
"""

ROLES = {
    "administrador": "Gestiona usuarios, roles, catálogo completo y auditoría.",
    "encargado": "Personal de bodega: catálogo, costos, ingresos de stock y proveedores.",
    "vendedor": "Usuario final: consulta stock, registra ventas y clientes.",
}

PERMISOS = {
    "usuarios:gestionar": "Crear usuarios, cambiar roles y desactivar cuentas",
    "roles:gestionar": "Ver y administrar roles y permisos",
    "perfil:ver_propio": "Ver los datos de la propia cuenta",
    "productos:leer": "Consultar catálogo y stock",
    "productos:ver_costo": "Ver precio de costo y proveedor de cada producto",
    "productos:crear": "Crear productos",
    "productos:editar": "Editar productos",
    "productos:eliminar": "Eliminar productos",
    "stock:ingresar": "Registrar ingresos de mercadería",
    "ventas:registrar": "Registrar ventas",
    "ventas:ver_propias": "Ver las ventas registradas por uno mismo",
    "ventas:ver_todas": "Ver las ventas de todos los vendedores",
    "clientes:crear": "Registrar clientes (se guardan seudonimizados)",
    "clientes:reidentificar": "Ver la identidad real detrás de un código de cliente",
    "proveedores:leer": "Ver proveedores con contacto enmascarado",
    "proveedores:gestionar": "Crear proveedores",
    "proveedores:ver_contacto": "Ver el contacto completo (descifrado) del proveedor",
    "reportes:anonimos": "Ver reportes agregados y anonimizados",
    "auditoria:leer": "Consultar el registro de auditoría",
}

MATRIZ = {
    "administrador": set(PERMISOS),  # todos
    "encargado": {
        "perfil:ver_propio", "productos:leer", "productos:ver_costo",
        "productos:crear", "productos:editar", "stock:ingresar",
        "proveedores:leer", "proveedores:gestionar", "proveedores:ver_contacto",
        "reportes:anonimos",
    },
    "vendedor": {
        "perfil:ver_propio", "productos:leer", "ventas:registrar",
        "ventas:ver_propias", "clientes:crear",
    },
}
