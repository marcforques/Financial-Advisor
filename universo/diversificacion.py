"""
Restricciones de diversificación real.

Segunda capa de la selección: impide la concentración SOLAPADA que las
restricciones por clase no detectan. El caso canónico: S&P 500 + Nasdaq +
MSCI World parecen tres activos distintos pero son casi la misma apuesta
(EEUU, grandes tecnológicas). Las restricciones por clase no lo ven porque
los tres son "renta variable"; estas restricciones por REGIÓN y SECTOR sí.

Genera restricciones lambda sobre los pesos, agrupando los activos por su
región y sector (según los metadatos del catálogo) y limitando el peso
agregado de cada grupo.
"""

from typing import Callable

from agents.perfil import PerfilInversor, NivelRiesgo
from universo.catalogo import metadatos, Region, Sector


# Máximo peso agregado por región, según perfil. Un conservador debe estar
# MÁS diversificado geográficamente (topes más bajos) que un agresivo.
_MAX_POR_REGION = {
    NivelRiesgo.CONSERVADOR: 0.45,
    NivelRiesgo.MODERADO: 0.55,
    NivelRiesgo.AGRESIVO: 0.70,
}

# Máximo peso agregado por sector concreto (no aplica a "amplio"/"na").
_MAX_POR_SECTOR = {
    NivelRiesgo.CONSERVADOR: 0.20,
    NivelRiesgo.MODERADO: 0.30,
    NivelRiesgo.AGRESIVO: 0.40,
}


def _indices_por(activos: list[str], clave: str, valor) -> list[int]:
    """
    Índices de los activos cuyo metadato `clave` es igual a `valor`.
    """
    indices = []
    for i, ticker in enumerate(activos):
        meta = metadatos(ticker)
        if meta[clave] == valor:
            indices.append(i)
    return indices
    

def restricciones_diversificacion(perfil: PerfilInversor, activos: list[str]) -> list[Callable]:
    """
    Genera restricciones de diversificación por región y sector.

    Parameters
    ----------
    perfil : PerfilInversor
        Perfil del inversor (su nivel de riesgo fija los topes).
    activos : list[str]
        Tickers en el orden que usará el optimizador (list(S.index)).

    Returns
    -------
    list[Callable]
        Restricciones lambda para el optimizador.
    """
    restricciones = []
    max_region = _MAX_POR_REGION[perfil.nivel_riesgo]
    max_sector = _MAX_POR_SECTOR[perfil.nivel_riesgo]
    
    # 1. Tope por REGIÓN: la exposición real de EEUU incluye la parte de
    #    los índices globales, pero como aproximación limitamos por la
    #    región etiquetada. (Refinamiento futuro: descomponer los globales.)
    regiones_presentes = {metadatos(t)["region"] for t in activos}
    for region in regiones_presentes:
        # No limitamos "no_aplica" (oro, materias_primas): no es una región.
        if region == Region.NA:
            continue
        indices = _indices_por(activos, "region", region)
        if indices:
            restricciones.append(
                lambda w, idx=indices, m=max_region: sum(w[i] for i in idx) <= m
            )
        
    # 2. Tope por SECTOR concreto (los sectoriales: tecnología, salud...).
    sectores_presentes = {metadatos(t)["sector"] for t in activos}
    for sector in sectores_presentes:
        # Solo limitamos sectores concretos, no "amplio" ni "na".
        if sector in (Sector.AMPLIO, Sector.NA):
            continue
        indices = _indices_por(activos, "sector", sector)
        if indices:
            restricciones.append(
                lambda w, idx=indices, m=max_sector: sum(w[i] for i in idx) <= m
            )
    
    return restricciones
        

    