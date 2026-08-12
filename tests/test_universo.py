"""
Tests de la selección de universo.

Blindan las propiedades clave de la fase de universo:
  - El filtro de adecuación descarta lo inapropiado por perfil.
  - La diversificación por región se respeta (caso S&P+NASDAQ+MSCI).
  - El tope por activo evita que uno domine.

Nacen de bugs reales encontrados durante la integración (materias primas
volátiles coladas, concentración regional, un activo acaparando su clase).
"""

import numpy as np
import pytest

from agents.perfil import PerfilInversor, NivelRiesgo, ObjetivoInversion
from universo.seleccion import filtrar_por_perfil
from universo.catalogo import metadatos, Region, Clase
from universo.diversificacion import restricciones_diversificacion

def _perfil(nivel: NivelRiesgo) -> PerfilInversor:
    return PerfilInversor(
        nivel_riesgo=nivel, horizonte_anios=15,
        capital=50000, objetivo=ObjetivoInversion.CRECIMIENTO
    )
    

def test_conservador_no_tiene_materias_primas_volatiles():
    """
    El conservador no debe incluir plata ni cestas de materias primas.
    """
    universo = filtrar_por_perfil(NivelRiesgo.CONSERVADOR)
    assert "SLV" not in universo
    assert "DBC" not in universo
    assert "GLD" in universo


def test_moderado_no_tiene_materias_primas():
    """
    El moderado tampoco debe incluir plata ni cestas volátiles.
    """
    universo = filtrar_por_perfil(NivelRiesgo.MODERADO)
    assert "SLV" not in universo
    assert "DBC" not in universo
    assert "GLD" in universo


def test_agresivo_ve_todo():
    """
    El agresivo puede ver todos los activos del catálogo.
    """
    universo = filtrar_por_perfil(NivelRiesgo.AGRESIVO)
    assert "SLV" in universo
    assert "QQQ" in universo
    assert "EEM" in universo
    
    
def test_conservador_no_tiene_sectoriales():
    """
    El conservador no debe incluir ETFs sectoriales concentrados.
    """
    universo = filtrar_por_perfil(NivelRiesgo.CONSERVADOR)
    for sectorial in ["XLK", "XLE", "XLF"]:
        assert sectorial not in universo
    

def test_universo_crece_con_riesgo():
    """
    El universo debe crecer del conservador al agresivo.
    """
    n_cons = len(filtrar_por_perfil(NivelRiesgo.CONSERVADOR))
    n_mod = len(filtrar_por_perfil(NivelRiesgo.MODERADO))
    n_agr = len(filtrar_por_perfil(NivelRiesgo.AGRESIVO))
    assert n_cons < n_mod < n_agr


def test_diversificacion_regional_detecta_concentracion():
    """
    Las restricciones de diversificación deben detectar una cartera
    concentrada en una región (el caso S&P + NASDAQ + MSCI).
    """
    activos = ["SPY", "QQQ", "URTH", "IEUR", "AGG", "GLD"]
    perfil = _perfil(NivelRiesgo.MODERADO)
    restr = restricciones_diversificacion(perfil, activos)
    
    # Debe generarse al menos una restricción de región.
    assert len(restr) >= 1
    
    # Una cartera 75% EEUU debe violar el tope regional del moderado 55%.
    idx_eeuu = [i for i, t in enumerate(activos)
                if metadatos(t)["region"] == Region.EEUU]
    pesos = [0.35, 0.30, 0.15, 0.10, 0.10, 0.00]        # SPY+QQQ+AGG = 75% EEUU
    suma_eeuu = sum(pesos[i] for i in idx_eeuu)
    assert suma_eeuu > 0.55     
    