"""
Generador de restricciones a partir del perfil.

Responsabilidad única: traducir un PerfilInversor en restricciones por
clase de activo que consume el optimizador.

Este módulo es código PURO y determinista. La clasificación de cada activo
(a qué clase pertenece) se lee del CATÁLOGO, que es la única fuente de
verdad del sistema, en lugar de mantener una tabla propia. Así, añadir un
activo al catálogo lo hace automáticamente reconocible aquí.
"""


from typing import Callable

from agents.perfil import PerfilInversor, NivelRiesgo
from universo.catalogo import metadatos, Clase



# Reglas por nivel de riesgo, por CLASE de activo (mín, máx) agregado.
_REGLAS_RIESGO = {
    NivelRiesgo.CONSERVADOR: {
        Clase.RENTA_VARIABLE: (0.10, 0.40),
        Clase.BONOS: (0.30, 0.60),
        Clase.MATERIAS_PRIMAS: (0.05, 0.25),
    },
    NivelRiesgo.MODERADO: {
        Clase.RENTA_VARIABLE: (0.30, 0.65),
        Clase.BONOS: (0.15, 0.40),
        Clase.MATERIAS_PRIMAS: (0.05, 0.25),
    },
    NivelRiesgo.AGRESIVO: {
        Clase.RENTA_VARIABLE: (0.50, 0.85),
        Clase.BONOS: (0.00, 0.25),
        Clase.MATERIAS_PRIMAS: (0.00, 0.20),
    }
}



def _indices_por_clase(activos: list[str], clase: str) -> list[int]:
    """
    Devuelve los índices de los actives que pertenecen a una clase.
    """
    return[i for i, ticker in enumerate(activos) if metadatos(ticker)["clase"] == clase]


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