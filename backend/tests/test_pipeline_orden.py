"""
Test de regresión: invariancia al orden de los activos.

Nace de un bug real: las restricciones se generaban con un orden de
activos distinto al que usaba el optimizador internamente (el de S,
alfabético), lo que hacía que los índices apuntaran a activos
equivocados y las restricciones se aplicaran mal.

Este test garantiza que, sea cual sea el orden en que se pasen los
activos, las restricciones por clase se respetan. Si alguien reintroduce
el bug, este test lo caza.
"""
import numpy as np
import pandas as pd
import pytest

from agents.perfil import PerfilInversor, NivelRiesgo, ObjetivoInversion
from agents.restricciones import generar_restricciones
from core.optimizer import optimizar_markowitz


@pytest.fixture
def mu_y_S_desordenadas():
    """
    Datos con los activos en orden alfabético (como los devuelve S),
    que es DISTINTO del orden 'natural' VUSA.AS, SUAG.L, SGLN.L, XMME.DE.
    """

    activos = ["SGLN.L", "SUAG.L", "VUSA.AS", "XMME.DE"]  # orden alfabético

    mu = pd.Series([0.08, 0.02, 0.13, 0.05], index=activos)
    
    S = pd.DataFrame(
        [
            [0.020, 0.003, 0.001, 0.005],
            [0.003, 0.003, 0.001, 0.001],
            [0.001, 0.001, 0.031, 0.028],
            [0.005, 0.001, 0.028, 0.043]
        ],
        index=activos,
        columns=activos
    )

    return mu, S


def test_restriccion_bonos_se_respeta_con_orden_alfabetico(mu_y_S_desordenadas):
    """
    El mínimo de bonos debe respetarse aunque los activos estén en
    orden alfabético (el orden real de S).
    """
    mu, S = mu_y_S_desordenadas
    orden = list(S.index)   # el orden canónico correcto
    
    perfil = PerfilInversor(
        nivel_riesgo=NivelRiesgo.MODERADO,
        horizonte_anios=20,
        capital=60000,
        objetivo=ObjetivoInversion.JUBILACION
    )
    
    restricciones = generar_restricciones(perfil, orden)
    resultado = optimizar_markowitz(mu, S, restricciones=restricciones)
    
    # El moderado exige bonos >= 15%. SUAG.L es el único bono.
    peso_bonos = resultado["pesos"]["SUAG.L"]
    assert peso_bonos >= 0.15 - 1e-4, (
        f"Bonos al {peso_bonos:.1%}, debería ser >= 15%"
    )
    
    
def test_orden_distinto_da_restricciones_coherentes(mu_y_S_desordenadas):
    """
    Generar restricciones con el orden de S y optimizar debe respetar
    los rangos de TODAS las clases.
    """
    mu, S = mu_y_S_desordenadas
    orden = list(S.index)
    
    perfil = PerfilInversor(
        nivel_riesgo=NivelRiesgo.CONSERVADOR,
        horizonte_anios=10,
        capital=50000,
        objetivo=ObjetivoInversion.PRESERVAR
    )
    
    restricciones = generar_restricciones(perfil, orden)
    resultado = optimizar_markowitz(mu, S, restricciones=restricciones)
    pesos = resultado["pesos"]
    
    # Conservador: renta variable (VUSA.AS+XMME.DE) como máximo 40%
    rv = pesos["VUSA.AS"] + pesos["XMME.DE"]
    assert rv <= 0.40 + 1e-4, f"Renta variable al {rv:.1%}, debería ser <= 40%"

    assert pesos["SUAG.L"] >= 0.30 - 1e-4, (
        f"Bonos al {pesos['SUAG.L']:.1%}, debería ser >= 30%"
    )
    
    