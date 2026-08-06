"""
Tests del pipeline de recomendación.

Prueban la lógica de orquestación SIN llamar al LLM real, usando dobles
de prueba (mocks) para las partes que dependen de OpenAI. Así los tests
son rápidos, gratuitos y reproducibles.

La conversión de views y el manejo del caso "sin views" son lógica pura
que se puede verificar directamente.
"""

from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from agents.perfil import PerfilInversor, NivelRiesgo, ObjetivoInversion
from agents.generador_views import View, ViewsGeneradas
from agents.pipeline import views_a_diccionario, recomendar_cartera


def test_views_a_diccionario_coniverte_bien():
    """
    La conversión de objetos View a diccionario debe ser correcta.
    """
    views = ViewsGeneradas(
        views=[
            View(activo="SPY", rentabilidad_esperada=0.10, justificacion="x"),
            View(activo="GLD", rentabilidad_esperada=0.06, justificacion="y")
        ]
    )
    
    resultado = views_a_diccionario(views)
    
    assert resultado == {"SPY": 0.10, "GLD": 0.06}
    


def test_views_a_diccionario_vacio():
    """
    Sin views, el diccionario debe estar vacío.
    """
    views = ViewsGeneradas(views=[])
    assert views_a_diccionario(views) == {}
    

@pytest.fixture
def datos_cartera():
    """
    Matriz de covarianzas y market caps de prueba.
    """
    activos = ["AGG", "EEM", "GLD", "SPY"]
    S = pd.DataFrame(
        [
            [0.003, 0.001, 0.003, 0.001],
            [0.001, 0.043, 0.005, 0.028],
            [0.003, 0.005, 0.020, 0.001],
            [0.001, 0.028, 0.001, 0.031]
        ],
        index=activos,
        columns=activos
    )
    market_caps = {"AGG": 100e9, "EEM": 20e9, "GLD": 60e9, "SPY": 400e9}
    return S, market_caps


def test_pipeline_sin_views_usa_equilibrio(datos_cartera):
    """
    Si el generador de views no produce views, el pipeline debe caer
    al equilibrio del mercado sin fallar.
    """
    S, market_caps = datos_cartera
    universo = ["AGG", "EEM", "GLD", "SPY"]
    
    perfil = PerfilInversor(
        nivel_riesgo=NivelRiesgo.MODERADO,
        horizonte_anios=15,
        capital=50000,
        objetivo=ObjetivoInversion.CRECIMIENTO
    )
    
    # Mock: forzamos que el generador de views devuelva la lista vacía, 
    # sin llamar al LLM real
    with patch("agents.pipeline.generar_views") as mock_views:
        mock_views.return_value = ViewsGeneradas(views=[])
        
        resultado = recomendar_cartera(perfil, universo, S, market_caps)
        
    # Debe haber producido una cartera válida.
    assert np.isclose(sum(resultado["pesos"].values()), 1.0)
    # Sin views usadas.
    assert resultado["views_usadas"] == []
    

def test_pipeline_con_views_las_aplica(datos_cartera):
    """
    Si el generador produce views, el pipeline debe incluirlas en el
    resultado con sus justificaciones.
    """
    S, market_caps = datos_cartera
    universo = ["AGG", "EEM", "GLD", "SPY"]
    
    perfil = PerfilInversor(
        nivel_riesgo=NivelRiesgo.AGRESIVO,
        horizonte_anios=25,
        capital=80000,
        objetivo=ObjetivoInversion.CRECIMIENTO
    )
    
    views_falsas = ViewsGeneradas(
        views=[View(activo="SPY", rentabilidad_esperada=0.11, justificacion="horizonte largo")]
    )
    
    with patch("agents.pipeline.generar_views") as mock_views:
        mock_views.return_value = views_falsas
        
        resultado = recomendar_cartera(perfil, universo, S, market_caps)
        
    #La cartera es válida y las views se registraron con justificación.
    assert np.isclose(sum(resultado["pesos"].values()), 1.0)
    assert len(resultado["views_usadas"]) == 1
    assert resultado["views_usadas"][0]["activo"] == "SPY"
    assert resultado["views_usadas"][0]["justificacion"] == "horizonte largo"