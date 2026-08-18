"""
Endpoints de gestión de carteras.

Expone las operaciones sobre carteras guardadas: crear/guardar, listar,
obtener, eliminar y rebalancear. El rebalanceo ofrece dos modalidades:
volver al plan original (rebalancear) o recalcular el óptimo (reoptimizar).

Los endpoints orquestan; la lógica vive en el repositorio, el optimizador
y el agente de rebalanceo.
"""

from fastapi import APIRouter, HTTPException

from pydantic import BaseModel

from api.modelos_cartera import CarteraGuardada
from persistencia.repositorio import RepositorioSQLite
from rebalanceo.agente import recomendar_rebalanceo
from agents.perfil import PerfilInversor
from api.dependencias import obtener_grafo


router = APIRouter(prefix="/carteras", tags=["carteras"])

# Repositorio compartido
_repo = RepositorioSQLite()


@router.post("")
def guardar_cartera(cartera: CarteraGuardada) -> dict:
    """
    Guarda una cartera y devuelve su id.
    """
    cartera_id = _repo.guardar(cartera)
    return {"id": cartera_id, "mensaje": "Cartera guardada correctamente"}

@router.get("/{usuario_id}")
def listar_carteras(usuario_id: str) -> list[CarteraGuardada]:
    """
    Lista todas las carteras de un usuario.
    """
    return _repo.listar_por_usuario(usuario_id)

@router.get("/detalle/{cartera_id}")
def obtener_cartera(cartera_id: str) -> CarteraGuardada:
    """
    Obtiene una cartera concreta por su id.
    """
    cartera = _repo.obtener(cartera_id)
    if cartera is None:
        raise HTTPException(status_code=404, detail="Cartera no encontrada")
    return cartera


@router.delete("/{cartera_id}")
def eliminar_cartera(cartera_id: str) -> dict:
    """
    Elimina una cartera.
    """
    if not _repo.eliminar(cartera_id):
        raise HTTPException(status_code=404, detail="Cartera no encontrada")
    return {"mensaje": "Cartera eliminada"}



class PeticionRebalanceo(BaseModel):
    """
    Parámetros para rebalancear una cartera guardada.
    """
    modo: str = "rebalancear"   # "rebalancear" (plan original) o "reoptimizar"
    precios_actuales: dict[str, float]  # precios de mercado actuales
    capital: float

@router.post("/{cartera_id}/rebalancear")
def rebalancear_cartera(cartera_id: str, peticion: PeticionRebalanceo) -> dict:
    """
    Analiza si conviene rebalancear una cartera guardada.

    Dos modos:
      - "rebalancear": vuelve a los pesos objetivo originales (control de
        riesgo, fiel al plan).
      - "reoptimizar": recalcula la cartera óptima para el perfil hoy
        (actualiza el plan; útil si el perfil o el mercado cambiaron).

    En ambos casos aplica el análisis de coste/impuestos y la banda de
    tolerancia del agente de rebalanceo.
    """
    cartera = _repo.obtener(cartera_id)
    if cartera is None:
        raise HTTPException(status_code=404, detail="Cartera no encontrada")
    
    # Pesos actuales
    pesos_actuales = cartera.pesos_actuales(peticion.precios_actuales)
    
    # Determinar los pesos objetivo según el modo
    if peticion.modo == "reoptimizar":
        pesos_objetivo = _recalcular_optimo(cartera)
    else:
        if cartera.pesos_objetivo is None:
            raise HTTPException(status_code=404, detail=("Esta cartera no tiene plan original guardado."
                                                         "Solo puede reoptimizarse."))
        pesos_objetivo = cartera.pesos_objetivo
        
    # Análisis de rebalanceo (banda de tolerancia + coste + impuestos).
    recomendacion = recomendar_rebalanceo(
        pesos_actuales=pesos_actuales,
        pesos_objetivo=pesos_objetivo,
        capital=peticion.capital,
        precios_compra=cartera.precios_compra_dict(),
        precios_actuales=peticion.precios_actuales
    )
    
    # Traducir a respuesta web
    return {
        "rebalancear": recomendacion.rebalancear,
        "modo": peticion.modo,
        "motivo": recomendacion.motivo,
        "plan": [
            {"activo": op.activo, "accion": op.accion, "importe": round(op.importe, 2)}
            for op in recomendacion.plan
        ],
        "coste_total": round(recomendacion.decision.coste_total, 2),
        "coste_transaccion": round(recomendacion.decision.coste_transaccion, 2),
        "impuesto": round(recomendacion.decision.impuesto, 2)
    }
    

def _recalcular_optimo(cartera: CarteraGuardada) -> dict[str, float]:
    """
    Recalcula la cartera óptima hoy para el perfil de la cartera.

    Ejecuta el grafo con el perfil guardado y devuelve los pesos óptimos
    actuales. Se usa en el modo 'reoptimizar'.
    """

    perfil = PerfilInversor(
        nivel_riesgo=cartera.nivel_riesgo,
        horizonte_anios=cartera.horizonte_anios,
        capital=cartera.capital_invertido(),
        objetivo=cartera.objetivo
    )

    # Reutilizamos el grafo del módulo principal.

    estado = {
        "perfil": perfil, "universo": [], "S": None, "market_caps": {},
        "views": None, "resultado": None, "explicacion": None,
        "perfil_valido": False, "mensaje_error": None,
    }
    final = obtener_grafo().invoke(estado)
    resultado = final.get("resultado")
    return resultado["pesos"] if resultado else {}    
    