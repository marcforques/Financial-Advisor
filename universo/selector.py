"""
Selector de universo: orquesta la selección completa.

Une las tres piezas de la fase de universo en un único punto de entrada:
  1. Filtra el catálogo por adecuación al perfil (seleccion.py).
  2. Genera las restricciones de clase de activo (restricciones.py).
  3. Genera las restricciones de diversificación real (diversificacion.py).

Devuelve el universo seleccionado y la lista COMBINADA de restricciones,
lista para el optimizador. Es la cara pública de todo el paquete universo/.
"""

from typing import Callable

import pandas as pd

from agents.perfil import PerfilInversor, NivelRiesgo
from agents.restricciones import generar_restricciones
from universo.seleccion import filtrar_por_perfil
from universo.diversificacion import restricciones_diversificacion


def seleccionar_universo(perfil: PerfilInversor) -> list[str]:
    """
    Devuelve los tickers adecuados para el perfil (primera capa).
    """
    return filtrar_por_perfil(perfil.nivel_riesgo)


def restricciones_completas(perfil: PerfilInversor, orden_activos: list[str]) -> list[Callable]:
    """
    Genera TODAS las restricciones para el optimizador, combinadas.

    Combina las restricciones por clase de activo con las de
    diversificación por región y sector. El orden de activos debe ser el
    canónico del optimizador (list(S.index)).

    Parameters
    ----------
    perfil : PerfilInversor
        Perfil del inversor.
    orden_activos : list[str]
        Tickers en el orden que usa el optimizador (list(S.index)).

    Returns
    -------
    list[Callable]
        Todas las restricciones lambda combinadas.
    """
    
    # Restricciones por clase de activo (renta variable, bonos, oro).
    restr_clase = generar_restricciones(perfil, orden_activos)
    
    # Restricciones de diversificación (región y sector).
    restr_div = restricciones_diversificacion(perfil, orden_activos)
    
    # Tope por activo individual: ningún activo domina la cartera.
    # Evita que un solo bono/acción acapare todo el cupo de su clase
    # (diversificación aparente a nivel de activo).
    max_por_activo = {
        NivelRiesgo.CONSERVADOR: 0.25,
        NivelRiesgo.MODERADO: 0.30,
        NivelRiesgo.AGRESIVO: 0.40,
    }[perfil.nivel_riesgo]

    restr_activo = [lambda w, m=max_por_activo: w <= m]
    
    # Combinadas: el optimizador debe respetarlas todas.
    return restr_clase + restr_div


   
    