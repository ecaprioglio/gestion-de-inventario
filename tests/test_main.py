import pytest

def test_ejemplo_pass():
    assert True

def test_inventario_base():
    # Simulación de una prueba básica para la API de inventario
    stock_inicial = 10
    venta = 2
    assert stock_inicial - venta == 8

def test_validar_nombre_proyecto():
    proyecto = "Gestion de Inventario - Moda y Calzado"
    assert "Inventario" in proyecto
