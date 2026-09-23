"""
Selección de universo por adecuación al perfil.

Primera capa de la selección: descarta del catálogo los activos
ESTRUCTURALMENTE INAPROPIADOS para el perfil, pero es permisiva con la
renta variable amplia y diversificada. El control fino de CUÁNTO puede
pesar cada clase lo hacen las restricciones (segunda capa).

Filosofía: un asesor no PROHÍBE la renta variable a un conservador, la
LIMITA. El filtro deja pasar lo apto; las restricciones ponen los topes.
"""

from agents.perfil import NivelRiesgo
from universo.catalogo import CATALOGO, NivelRiesgoActivo, Clase, Region, Sector
from collections import Counter


def _es_amplio(activo: dict) -> bool:
    """
    Un activo es 'amplio' si es un índice diversificado (no sectorial,
    no de un solo país emergente). Los amplios son más admisibles.
    """
    # Solo la renta variable puede ser "amplia".
    if activo["clase"] != Clase.RENTA_VARIABLE:
        return False
    
    # Sectorial -> concentrado
    if activo["sector"] != Sector.AMPLIO:
        return False  
    
    # Renta variable de emergentes -> concentrada/volátil.    
    if activo["region"] == Region.EMERGENTES:
        return False 
    return True


def _es_admisible(activo: dict, nivel: NivelRiesgo) -> bool:
    """
    Decide si un activo es apropiado para un perfil.

    Reglas por perfil:
      - Conservador: bonos (cualquiera) + renta variable AMPLIA + oro.
        Nada sectorial, nada emergente, nada de materias primas volátiles.
      - Moderado: todo lo anterior + activos de riesgo medio, incluidos
        algunos concentrados (sectores defensivos). Sin riesgo alto puro.
      - Agresivo: todo.
    """
    clase = activo["clase"]
    riesgo = activo["riesgo"]
    amplio = _es_amplio(activo)

    # ─── AGRESIVO ───
    if nivel == NivelRiesgo.AGRESIVO:
        return True  # el agresivo puede ver todo

    # ─── MODERADO ───
    if nivel == NivelRiesgo.MODERADO:
        # Materias primas: solo oro (plata y cestas son demasiado volátiles).
        if clase == Clase.MATERIAS_PRIMAS:
            return activo["ticker"] == "SGLN.L"
        # Renta variable de riesgo alto concentrada: fuera.
        if riesgo == NivelRiesgoActivo.ALTO and not amplio:
            return False
        # Bonos de riesgo alto (p. ej. emergentes): fuera para moderado.
        if clase == Clase.BONOS and riesgo == NivelRiesgoActivo.ALTO:
            return False
        return True

    # ─── CONSERVADOR ─── 
    # Bonos de riesgo no-alto.
    if clase == Clase.BONOS:
        return riesgo != NivelRiesgoActivo.ALTO
    # Renta variable solo si es amplia y de riesgo no-alto.
    if clase == Clase.RENTA_VARIABLE:
        return amplio and riesgo != NivelRiesgoActivo.ALTO
    # Materias primas: solo oro.
    if clase == Clase.MATERIAS_PRIMAS:
        return activo["ticker"] == "SGLN.L"
    return False


def filtrar_por_perfil(nivel_riesgo: NivelRiesgo) -> list[str]:
    """
    Devuelve los tickers apropiados para un nivel de riesgo.
    """
    return [
        activo["ticker"]
        for activo in CATALOGO
        if _es_admisible(activo, nivel_riesgo)
    ]


def resumen_seleccion(nivel_riesgo: NivelRiesgo) -> dict:
    """
    Resumen de qué entra y qué se descarta, para transparencia.
    """

    seleccionados = [a for a in CATALOGO if _es_admisible(a, nivel_riesgo)]
    descartados = [a for a in CATALOGO if not _es_admisible(a, nivel_riesgo)]

    return {
        "n_seleccionados": len(seleccionados),
        "n_descartados": len(descartados),
        "por_clase": Counter(a["clase"].value for a in seleccionados),
        "por_region": Counter(a["region"].value for a in seleccionados),
        "descartados": [a["ticker"] for a in descartados],
    }