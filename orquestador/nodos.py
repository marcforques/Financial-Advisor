"""
Nodos del grafo de orquestación.

Cada nodo envuelve a un agente existente de la Fase 4. El patrón es
siempre el mismo: lee del estado lo que necesita, llama al agente, y
devuelve un diccionario con los campos del estado que ha actualizado.

IMPORTANTE: los agentes NO se reescriben. Estos nodos son adaptadores
finos que conectan los agentes al grafo. Toda la lógica sigue viviendo
en los módulos de agents/ y core/.
"""

from agents.generador_views import generar_views
from agents.restricciones import generar_restricciones
from agents.explicador import explicar_cartera
from agents.pipeline import views_a_diccionario
from core.optimizer import optimizar_black_litterman, rentabilidades_equilibrio, optimizar_markowitz
from orquestador.estado import PortfolioState


def nodo_validar_perfil(state: PortfolioState) -> dict:
    """
    Comprueba que el perfil es válido antes de seguir.

    Escribe en `perfil_valido` el resultado de la validación, que la
    arista condicional usará para decidir el flujo. Como el perfil ya es
    un objeto Pydantic validado, aquí comprobamos coherencia adicional:
    que el universo no esté vacío y el capital sea razonable.
    """
    perfil = state["perfil"]
    universo = state["universo"]
    
    if len(universo) < 2:
        return {
            "perfil_valido": False,
            "mensaje_error": (
                "No se puede construir una cartera diversificada con menos "
                "de dos activos. Amplía el universo de inversión."
            )
        }
    
    if perfil.capital <= 0:
        return {
            "perfil_valido": False,
            "mensaje_error": (
                "El capital a invertir debe ser mayor que cero."
            )
        }
        
    if perfil.horizonte_anios < 1:
        return {
            "perfil_valido": False,
            "mensaje_error": (
                "El horizonte de inversión debe ser de al menos un año."
            )
        }

    return {"perfil_valido": True, "mensaje_error": None}


def nodo_generar_views(state: PortfolioState) -> dict:
    """
    Genera las views de Black-Litterman a partir del perfil (LLM).
    """
    views = generar_views(state["perfil"], state["universo"])
    return {"views": views}


def nodo_optimizar(state: PortfolioState) -> dict:
    """
    Optimiza la cartera con Black-Litterman y las restricciones.
    """
    perfil= state["perfil"]
    S = state["S"]
    market_caps = state["market_caps"]
    views = state["views"]
    
    # Restricciones desde el perfil, en el orden canónico de S.
    orden_canonico = list(S.index)
    restricciones = generar_restricciones(perfil, orden_canonico)
    
    views_dict = views_a_diccionario(views) if views else {}
    
    if not views_dict:
        prior = rentabilidades_equilibrio(market_caps, S)
        resultado = optimizar_markowitz(prior, S, restricciones=restricciones)
        resultado["posterior"] = dict(prior)
    else:
        resultado = optimizar_black_litterman(S, market_caps, views_dict, restricciones=restricciones)
    
    # Guardamos las views con justificación para el explicador.
    resultado["views_usadas"] = [
        {"activo": v.activo, "justificacion": v.justificacion}
        for v in (views.views if views else [])
    ]
    
    return {"resultado": resultado}
    
    
def nodo_explicar(state: PortfolioState, kb) -> dict:
    """
    Genera la explicación en lenguaje natural (LLM + RAG).

    Nota: este nodo necesita la base de conocimiento (kb). Como los nodos
    de LangGraph solo reciben el estado, la kb se inyecta al construir el
    grafo mediante un cierre (closure). Se explica en el grafo.
    """
    explicacion = explicar_cartera(state["perfil"], state["resultado"], kb)
    return {"explicacion": explicacion}
        

def nodo_informar_error(state: PortfolioState) -> dict:
    """
    Nodo terminal de error.

    Se ejecuta cuando la validación falla. Su trabajo es dejar el estado
    en una forma coherente y presentable: coge el mensaje de error y lo
    coloca como 'explicacion', de modo que el usuario siempre recibe una
    respuesta en lenguaje natural, nunca un resultado vacío.
    """
    mensaje = state.get("mensaje_error") or (
        "No se pudo generar la cartera con los datos proporcionados."
    )
    
    explicacion = (
        f"No ha sido posible generar una recomendación de cartera.\n\n"
        f"Motivo: {mensaje}\n\n"
        f"Por favor, revisa los datos e inténtalo de nuevo."
    )
    
    return {"explicacion": explicacion}