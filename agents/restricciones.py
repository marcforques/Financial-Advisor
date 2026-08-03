"""
Generador de restricciones a partir del perfil.

Responsabilidad única: traducir un PerfilInversor en la lista de
restricciones que consume el optimizador.

Este módulo es código PURO y determinista, sin IA: las reglas que
asignan restricciones a cada perfil son política de negocio explícita
y auditable, no interpretación difusa. Un regulador debe poder leer
estas reglas y entender exactamente por qué un conservador recibe la
cartera que recibe.
"""

from typing import Callable

from agents.perfil import PerfilInversor, NivelRiesgo

# Reglas por nivel de riesgo. Cada perfil define límites mínimos de
# activos "refugio" (bonos, oro) y máximos de activos de riesgo.
# Estos valores son decisiones de negocio documentadas en la memoria.
_REGLAS_RIESGO = {
    NivelRiesgo.CONSERVADOR: {
        "min_refugio": 0.50,    # al menos 50% en activos refugio
        "max_por_activo": 0.35  # ningún activo domina
    },
    NivelRiesgo.MODERADO: {
        "min_refugio": 0.25,
        "max_por_activo": 0.45
    },
    NivelRiesgo.AGRESIVO: {
        "min_refugio": 0.05,
        "max_por_activo": 0.60
    }
}

# Qué activos se considern "refugio" (defensivos).
_ACTIVOS_REFUGIO = {"AGG", "GLD"}


def generar_restricciones(perfil: PerfilInversor, activos: list[str]) -> list[Callable]:
    """
    Genera las restricciones del optimizador a partir del perfil.

    Parameters
    ----------
    perfil : PerfilInversor
        Perfil del inversor con su nivel de riesgo y horizonte.
    activos : list[str]
        Lista ordenada de tickers de la cartera. El orden debe coincidir
        con el que espera el optimizador (el de mu/S).

    Returns
    -------
    list[Callable]
        Lista de funciones lambda listas para pasar al optimizador.
    """
    
    reglas = _REGLAS_RIESGO[perfil.nivel_riesgo]
    restricciones = []
    
    # 1. Tope máximo por activo (evita concentración)
    max_activo = reglas["max_por_activo"]
    restricciones.append(lambda w: w <= max_activo)
    
    # 2. Mínimo agregado en activos refugio.
    #   Localizamos los índices de los activos refugio presentes.
    indices_refugio = [
        i for i, activo in enumerate(activos) if activo in _ACTIVOS_REFUGIO
    ]
    
    if indices_refugio:
        min_refugio = reglas["min_refugio"]
        # La suma de los pesos refugio debe superar el mínimo.
        restricciones.append(
            lambda w: sum(w[i] for i in indices_refugio) >= min_refugio
        )
    return restricciones