"""
Generador de restricciones a partir del perfil.

Responsabilidad única: traducir un PerfilInversor en la lista de
restricciones que consume el optimizador.

Este módulo es código PURO y determinista, sin IA. Las restricciones se
definen por CLASE DE ACTIVO (renta variable, bonos, oro), no agrupando
activos defensivos en un cajón común. Esto evita que un perfil que pide
estabilidad acabe sin bonos porque el oro cubrió por sí solo el mínimo
defensivo: cada clase tiene su propio suelo y techo.
"""

from typing import Callable

from agents.perfil import PerfilInversor, NivelRiesgo

class ClaseActivo:
    """
    Clases de activos reconocidas por el sistema
    """
    RENTA_VARIABLE = "renta_variable"
    BONOS = "bonos"
    ORO = "oro"
    


# Mapa de cada ticker a su clase de activo.
# En el sistema completo esto lo proporciona el agente de universo.
CLASIFICACION_ACTIVOS = {
    "SPY": ClaseActivo.RENTA_VARIABLE,
    "EEM": ClaseActivo.RENTA_VARIABLE,
    "AGG": ClaseActivo.BONOS,
    "ORO": ClaseActivo.ORO
}


# Reglas por nivel de riesgo. Cada perfil define límites mínimos de
# activos "refugio" (bonos, oro) y máximos de activos de riesgo.
# Estos valores son decisiones de negocio documentadas en la memoria.
_REGLAS_RIESGO = {
    NivelRiesgo.CONSERVADOR: {
        ClaseActivo.RENTA_VARIABLE: (0.10, 0.40),
        ClaseActivo.BONOS: (0.30, 0.60),
        ClaseActivo.ORO: (0.05, 0.25)
    },
    NivelRiesgo.MODERADO: {
        ClaseActivo.RENTA_VARIABLE: (0.30, 0.65),
        ClaseActivo.BONOS: (0.15, 0.40),
        ClaseActivo.ORO: (0.05, 0.25)
    },
    NivelRiesgo.AGRESIVO: {
        ClaseActivo.RENTA_VARIABLE: (0.50, 0.85),
        ClaseActivo.BONOS: (0.00, 0.25),
        ClaseActivo.ORO: (0.00, 0.20)
    }
}


def _indices_por_clase(activos: list[str], clase: str) -> list[int]:
    """
    Devuelve los índices de los actives que pertenecen a una clase.
    """
    return[i for i, activo in enumerate(activos) if CLASIFICACION_ACTIVOS.get(activo) == clase]


def generar_restricciones(perfil: PerfilInversor, activos: list[str]) -> list[Callable]:
    """
    Genera las restricciones del optimizador a partir del perfil.

    Para cada clase de activo presente en el universo, impone un mínimo y
    un máximo agregado según el nivel de riesgo del perfil. Así se garantiza
    que cada clase (bonos, renta variable, oro) tenga la presencia que el
    perfil requiere, sin que una clase supla a otra.
    
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
    
    for clase, (minimo, maximo) in reglas.items():
        indices = _indices_por_clase(activos, clase)
        
        if not indices:
            continue  # esa clave no estña en el universo, se omite
        
        # Mínimo agregado de la clase (si es > 0)
        if minimo > 0:
            restricciones.append(lambda w, idx=indices, m=minimo: sum(w[i] for i in idx) >= m)
            
        # Máximo agregado de la clase 
        restricciones.append(lambda w, idx=indices, M=maximo: sum(w[i] for i in idx) <= M)

    return restricciones