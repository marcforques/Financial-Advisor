"""
Tests del grafo de orquestación.

Verifican los dos caminos del grafo:
  - Camino válido: perfil correcto -> cartera + explicación.
  - Camino de error: perfil/universo inválido -> mensaje de error, sin
    llegar a optimizar.

Se usan mocks para las llamadas al LLM (views y explicador), de modo que
los tests son deterministas y no dependen de la API.
"""

from unittest.mock import patch

import pandas as pd
import pytest

from agents.perfil import PerfilInversor, NivelRiesgo, ObjetivoInversion
from agents.generador_views import ViewsGeneradas, View
from orquestador.grafo import construir_grafo
from orquestador.estado import PortfolioState


class _KBFalsa:
    """
    Base de conocimiento falsa: no llama a ChromaDB en los tests.
    """
    
    def buscar(self, consulta, n_resultados=2):
        return ["Definición de referencia de prueba."]
    

@pytest.fixture
def datos():
    """
    Matriz de covarianzas prueba.
    """
    activos = ["SUAG.L", "XMME.DE", "SGLN.L", "VUSA.AS"]
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
    market_caps = {"SUAG.L": 100e9, "XMME.DE": 20e9, "SGLN.L": 60e9, "VUSA.AS": 400e9}
    return S,market_caps


def _estado(perfil, universo, S, market_caps) -> PortfolioState:
    return {
        "perfil": perfil, 
        "universo": universo,
        "S": S,
        "market_caps": market_caps,
        "views": None,
        "resultado": None,
        "explicacion": None,
        "perfil_valido": False,
        "mensaje_error": None
    }


def test_camino_valido_produce_cartera(datos):
    """
    Con perfil y universo válidos, el grafo produce cartera y explicación.
    """
    S, market_caps = datos
    perfil = PerfilInversor(
        nivel_riesgo=NivelRiesgo.MODERADO,
        horizonte_anios=20,
        capital=60000,
        objetivo=ObjetivoInversion.JUBILACION
    )
    estado = _estado(perfil, ["SUAG.L", "XMME.DE", "SGLN.L", "VUSA.AS"], S, market_caps)

    grafo = construir_grafo(_KBFalsa())

    # Mock del LLM de views y del explicador.
    views_falsas = ViewsGeneradas(
        views=[View(activo="VUSA.AS", rentabilidad_esperada=0.10, justificacion="x")]
    )
    with patch("orquestador.nodos.generar_views", return_value=views_falsas), \
        patch("orquestador.nodos.explicar_cartera", return_value="Explicación de prueba."):
        final = grafo.invoke(estado)
        
    assert final["perfil_valido"] is True
    assert final["resultado"] is not None
    assert final["explicacion"] == "Explicación de prueba."
    
    
def test_camino_error_perfil_invalido(datos):
    """
    Con un perfil de capital inválido, el grafo va al nodo de error
    sin llegar a optimizar.
    """
    
    S, market_caps = datos
    perfil = PerfilInversor.model_construct(
        nivel_riesgo=NivelRiesgo.MODERADO,
        horizonte_anios=20,
        capital=-100,
        objetivo=ObjetivoInversion.JUBILACION,
        matices=[]
    )
    estado = _estado(perfil, ["SUAG.L", "XMME.DE", "SGLN.L", "VUSA.AS"], S, market_caps)

    grafo = construir_grafo(_KBFalsa())
    final = grafo.invoke(estado)

    # No se generó cartera, pero hay explicación de error.
    assert final["perfil_valido"] is False
    assert final["resultado"] is None
    assert final["explicacion"] is not None
    
    
def test_camino_error_no_llama_al_llm(datos):
    """
    El camino de error no debe llegar a generar views (ni gastar LLM).
    """
    
    S, market_caps = datos
    perfil = PerfilInversor.model_construct(
        nivel_riesgo=NivelRiesgo.MODERADO,
        horizonte_anios=20,
        capital=-100,
        objetivo=ObjetivoInversion.JUBILACION,
        matices=[]
    )
    estado = _estado(perfil, ["SUAG.L", "XMME.DE", "SGLN.L", "VUSA.AS"], S, market_caps)

    grafo = construir_grafo(_KBFalsa())

    # Si el flujo llegara a generar_views, este mock lo detectaría.
    with patch("orquestador.nodos.generar_views") as mock_views:
        grafo.invoke(estado)
        mock_views.assert_not_called()  # nunca debe llamarse