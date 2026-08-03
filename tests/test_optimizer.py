"""
Tests del módulo de optimización.

Verifican propiedades que deben cumplirse SIEMPRE, independientemente de
los datos concretos: los pesos suman 1, se respetan las restricciones, y
Black-Litterman sin views recupera el equilibrio de mercado.
"""

import numpy as np
import pandas as pd
import pytest

from core.optimizer import optimizar_markowitz, rentabilidades_equilibrio, optimizar_black_litterman


@pytest.fixture
def datos_mercado():
    """
    Ingredientes de prueba: 3 activos con rentabilidades y covarianzas
    realistas pero controladas.
    """
    activos = ["A", "B", "C"]
    mu = pd.Series([0.10, 0.06, 0.08], index=activos)
    
    # Matriz de covarianzas simétrica y definida positiva (válida).
    S = pd.DataFrame(
        [
            [0.040, 0.002, 0.001],
            [0.002, 0.030, 0.003],
            [0.001, 0.003, 0.020]
        ],
        index=activos,
        columns=activos
    )
    return mu, S


def test_pesos_suman_uno(datos_mercado):
    """
    Los pesos de la cartera deben sumar 1 (se invierte el 100%).
    """
    mu, S = datos_mercado
    resultado = optimizar_markowitz(mu, S)
    
    suma = sum(resultado["pesos"].values())
    assert np.isclose(suma, 1.0)
    

def test_pesos_no_negativos(datos_mercado):
    """
    Sin posiciones cortas: ningún peso puede ser negativo.
    """  
    mu, S = datos_mercado
    resultado = optimizar_markowitz(mu, S)
    
    for peso in resultado["pesos"].values():
        assert peso >= -1e-6    # Margen mínimo por ruido numérico
    

def test_restriccion_maximo_se_respeta(datos_mercado):
    """
    Si se impone un máximo del 40%, ningún activo debe superarlo.
    """
    mu, S = datos_mercado
    restr = [lambda w: w <= 0.40]
    
    resultado = optimizar_markowitz(mu, S, restricciones=restr)
    
    for peso in resultado["pesos"].values():
        assert peso <= 0.40 + 1e-6


def test_restricciones_minimo_se_respeta(datos_mercado):
    """
    Si se impone un mínimo del 10%, todos los activos deben alcanzarlo.
    """
    mu, S = datos_mercado
    restr = [lambda w: w >= 0.10]
    
    resultado = optimizar_markowitz(mu, S, restricciones=restr)

    for peso in resultado["pesos"].values():
        assert peso >= 0.10 - 1e-6
        

def test_equilibrio_devuelve_serie_correcta(datos_mercado):
    """
    Las rentabilidades de equilibrio deben tener un valor por activo.
    """
    mu, S = datos_mercado
    market_caps = {"A": 100e-9, "B": 50e9, "C": 30e9}
    
    prior = rentabilidades_equilibrio(market_caps, S)
    
    assert len(prior) == 3
    assert set(prior.index) == {"A", "B", "C"}
    

def test_black_litterman_incluye_posterior(datos_mercado):
    """
    El resultado de Black-Litterman debe incluir el posterior.
    """
    mu, S = datos_mercado
    market_caps =   {"A": 100e9, "B": 50e9, "C": 30e9}
    views = {"A": 0.15}
    
    resultado = optimizar_black_litterman(S, market_caps, views)
    
    assert "posterior" in resultado
    assert "pesos" in resultado
    # Los pesos siguen sumando 1 también con Black-Litterman.
    assert np.isclose(sum(resultado["pesos"].values()), 1.0)
    
    
def test_view_alcista_aumenta_peso(datos_mercado):
    """
    Una view alcista en un activo debe darle MÁS peso que sin la view.
    """
    mu, S = datos_mercado
    market_caps = {"A": 100e9, "B": 50e9, "C": 30e9}
    
    # Sin view (view neutra en su propio equilibrio): peso base de A.
    prior = rentabilidades_equilibrio(market_caps, S)
    sin_view = optimizar_black_litterman(S, market_caps, views={"A": prior["A"]})
    
    # COn view alcista fuerte en A.
    con_view = optimizar_black_litterman(S, market_caps, views={"A": 0.20})
    
    assert con_view["pesos"]["A"] > sin_view["pesos"]["A"]
    

