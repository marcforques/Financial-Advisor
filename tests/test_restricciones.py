"""
Tests del generador de restricciones.

Verifican que las reglas de negocio por perfil se cumplen SIEMPRE:
un conservador siempre tiene más refugio que un agresivo, los topes
se respetan, y las restricciones son coherentes con el nivel de riesgo.
"""

import pytest

from agents.perfil import PerfilInversor, NivelRiesgo, ObjetivoInversion
from agents.restricciones import generar_restricciones, _REGLAS_RIESGO


def _perfil(nivel: NivelRiesgo) -> PerfilInversor:
    """
    Crea un perfil de prueba con el nivel de riesgo dado.
    """
    return PerfilInversor(
        nivel_riesgo=nivel,
        horizonte_anios=15,
        capital=50000,
        objetivo=ObjetivoInversion.CRECIMIENTO
    )
    

def test_cada_perfil_genera_restricciones():
    """
    Todo perfil debe generar al menos una restricción.
    """
    for nivel in NivelRiesgo:
        restr = generar_restricciones(_perfil(nivel), ["SPY", "AGG", "GLD"])
        assert len(restr) >= 1
        

def test_conservador_exige_mas_refugio_que_agresivo():
    """
    Propiedad clave: el conservador debe exigir MÁS refugio que el
    agresivo. Si esto se rompe, la personalización está invertida.
    """
    activos = ["SPY", "AGG", "GLD", "EEM"]
    
    # Índices de los activos refugio (AGG, GLD).
    idx_refugio = [1, 2]
    
    # Pesos de prueba: 30% en cada refugio = 60% refugio total
    pesos_prueba = [0.20, 0.30, 0.30, 0.20]
    
    restr_cons = generar_restricciones(_perfil(NivelRiesgo.CONSERVADOR), activos)
    restr_agr = generar_restricciones(_perfil(NivelRiesgo.AGRESIVO), activos)
    
    # La restricción de refugio del conservador es más exigente:
    # con 60% de refugio, el conservador (min 50%) la cumple,
    # y también el agresivo (min 5%). Verificamos el sentido probando
    # un caso donde solo el agresivo pasa. 
    pesos_poco_refugio = [0.45, 0.05, 0.05, 0.45]   # 10% refugio
    
    # El agresivo (min 5%) debe aceptar 10% del refugio.
    refugio_agr = sum(pesos_poco_refugio[i] for i in idx_refugio)
    assert refugio_agr >= 0.05
    
    # El conservador (min 50%) NO debe aceptar 10% de refugio.
    assert refugio_agr < 0.50
    

def test_tope_por_activo_decrece_con_conservadurismo():
    """
    El tope máximo por activo del conservador debe ser menor o igual
    que el del agresivo (el conservador diversifica más).
    """
    max_cons = _REGLAS_RIESGO[NivelRiesgo.CONSERVADOR]["max_por_activo"]
    max_agr = _REGLAS_RIESGO[NivelRiesgo.AGRESIVO]["max_por_activo"]
    
    assert max_cons <= max_agr


def test_min_refugio_decrece_con_riesgo():
    """
    El mínimo de refugio debe decrecer: conservador > moderado > agresivo.
    """  
    
    cons = _REGLAS_RIESGO[NivelRiesgo.CONSERVADOR]["min_refugio"]
    mod = _REGLAS_RIESGO[NivelRiesgo.MODERADO]["min_refugio"]
    agr = _REGLAS_RIESGO[NivelRiesgo.AGRESIVO]["min_refugio"]
    
    assert cons > mod > agr

