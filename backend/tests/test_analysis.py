"""
Tests del módulo de análisis cuantitativo.

Verifican que las rentabilidades, covarianzas y métricas se calculan
correctamente, usando datos sintéticos controlados donde conocemos el
resultado esperado de antemano.
"""

import numpy as np
import pandas as pd
import pytest

from core.analysis import rentabilidades_esperadas, matriz_covarianzas, metricas_cartera


@pytest.fixture
def precios_sinteticos():
    """ 
    Precios de prueba: 2 activos, 4 días, valores controlados
    """
    fechas = pd.date_range("2020-01-01", periods=4, freq="D")
    return pd.DataFrame(
        {
            "A": [100.0, 110.0, 121.0, 133.1],  # sube un 10% cada día
            "B": [100.0, 100.0, 100.0, 100.0]   # constante
        },
        index=fechas
    )
    

def test_covarianza_es_cuadrada_y_simetrica(precios_sinteticos):
    """
    La matriz de covarianzas debe ser cuadrada y simétrica.
    """
    S = matriz_covarianzas(precios_sinteticos)
    
    # Cuadrada: tantas filas como columnas, = nº activos.
    assert S.shape[0] == S.shape[1] == 2
    
    # Simétrica: Cov(A, B) == Cov(B, A).
    assert np.isclose(S.loc["A", "B"], S.loc["B", "A"])
    
    
def test_activo_constante_tiene_volatilidad_cero(precios_sinteticos):
    """
    Un activo con precio constante no tiene riesgo: varianza = 0.
    """
    S = matriz_covarianzas(precios_sinteticos)
    
    # El activo B nunca cambia, su varianza debe ser (casi) cero.
    assert np.isclose(S.loc["B", "B"], 0.0)
    

def test_metricas_pesos_extremos(precios_sinteticos):
    """
    Poner todo el peso en un activo debe dar sus propias métricas.
    """
    mu = rentabilidades_esperadas(precios_sinteticos)
    S = matriz_covarianzas(precios_sinteticos)

    # Todo en A: la rentabilidad de la cartera debe der la de A.
    metricas = metricas_cartera({"A": 1.0, "B": 0.0}, mu, S)
    assert np.isclose(metricas["rentabilidad"], mu["A"])
    

def test_suma_pesos_no_afecta_estructura(precios_sinteticos):
    """
    Las métricas deben calcularse sin error con pesos válidos.
    """
    mu = rentabilidades_esperadas(precios_sinteticos)
    S =matriz_covarianzas(precios_sinteticos)
    
    metricas = metricas_cartera({"A": 0.5, "B": 0.05}, mu, S)
    
    # Las tres métricas deben existir y ser números
    assert "rentabilidad" in metricas
    assert "volatilidad" in metricas
    assert isinstance(metricas["sharpe"], float)
      