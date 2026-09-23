"""
Endpoints de gestión de carteras.

Expone las operaciones sobre carteras guardadas: crear/guardar, listar,
obtener, eliminar y rebalancear. El rebalanceo ofrece dos modalidades:
volver al plan original (rebalancear) o recalcular el óptimo (reoptimizar).

Los endpoints orquestan; la lógica vive en el repositorio, el optimizador
y el agente de rebalanceo.

Todas las rutas requieren sesión (Depends(obtener_usuario_actual) y/o
Depends(obtener_repositorio)): el usuario se identifica por el JWT de la
cabecera Authorization, nunca por un id que venga en la URL o en el
cuerpo de la petición.
"""

from fastapi import APIRouter, Depends, HTTPException

from pydantic import BaseModel

from api.modelos_auth import UsuarioSesion
from api.modelos_cartera import CarteraGuardada
from api.seguridad import obtener_usuario_actual, obtener_repositorio
from persistencia.repositorio import RepositorioSupabase
from rebalanceo.agente import recomendar_rebalanceo
from agents.perfil import PerfilInversor
from api.dependencias import obtener_grafo
from core.data import obtener_precios_actuales

router = APIRouter(prefix="/carteras", tags=["carteras"])


@router.post("")
def guardar_cartera(
    cartera: CarteraGuardada,
    usuario: UsuarioSesion = Depends(obtener_usuario_actual),
    repo: RepositorioSupabase = Depends(obtener_repositorio),
) -> dict:
    """
    Guarda una cartera y devuelve su id.
    """
    # El usuario_id nunca sale del cuerpo de la petición: lo fijamos aquí
    # con el id ya verificado del token. Si el JSON trae un usuario_id
    # distinto (a mano o por error del cliente), se ignora.
    cartera.usuario_id = usuario.id
    cartera_id = repo.guardar(cartera)
    return {"id": cartera_id, "mensaje": "Cartera guardada correctamente"}


@router.get("/detalle/{cartera_id}")
def obtener_cartera(
    cartera_id: str,
    repo: RepositorioSupabase = Depends(obtener_repositorio),
) -> CarteraGuardada:
    """
    Obtiene una cartera concreta por su id.

    Si la cartera es de otro usuario, RLS hace que la consulta no
    devuelva ninguna fila (no un error de permisos), así que esto
    responde 404 igual que si no existiera. Es intencional: no revela
    la existencia de carteras ajenas.
    """
    cartera = repo.obtener(cartera_id)
    if cartera is None:
        raise HTTPException(status_code=404, detail="Cartera no encontrada")
    return cartera


@router.get("/precios-actuales")
def precios_actuales(
    tickers: str,
    usuario: UsuarioSesion = Depends(obtener_usuario_actual),
) -> dict[str, float]:
    """
    No toca datos de usuario, pero exige sesión igualmente: evita que
    cualquiera use la API como proxy gratuito a yfinance.
    """
    lista = tickers.split(",")
    return obtener_precios_actuales(lista)


@router.get("")
def listar_carteras(
    usuario: UsuarioSesion = Depends(obtener_usuario_actual),
    repo: RepositorioSupabase = Depends(obtener_repositorio),
) -> list[CarteraGuardada]:
    """
    Lista todas las carteras del usuario autenticado.

    Antes era GET /carteras/{usuario_id}, con el id puesto a mano en la
    URL: cualquiera podía leer las carteras de cualquiera cambiando el
    path (IDOR). Ahora el usuario sale del token, no de la URL.
    """
    return repo.listar_por_usuario(usuario.id)


@router.delete("/{cartera_id}")
def eliminar_cartera(
    cartera_id: str,
    repo: RepositorioSupabase = Depends(obtener_repositorio),
) -> dict:
    """
    Elimina una cartera.
    """
    if not repo.eliminar(cartera_id):
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
def rebalancear_cartera(
    cartera_id: str,
    peticion: PeticionRebalanceo,
    repo: RepositorioSupabase = Depends(obtener_repositorio),
) -> dict:
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
    cartera = repo.obtener(cartera_id)
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
