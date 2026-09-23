"""
Construcción del grafo de orquestación con LangGraph.

Ensambla los nodos (agentes) en un grafo de estado con aristas que
definen el flujo. Incluye una arista condicional que decide, según la
validez del perfil, si el sistema continúa o se detiene.

Este grafo es la orquestación formal que sustituye al pipeline lineal:
mismo resultado, pero con control de flujo dinámico y estado compartido.
"""

from functools import partial

from langgraph.graph import StateGraph, END

from orquestador.estado import PortfolioState
from orquestador.nodos import nodo_validar_perfil, nodo_seleccionar_universo, nodo_generar_views, nodo_optimizar, nodo_explicar, nodo_informar_error


def _decidir_tras_validar(state: PortfolioState) -> str:
    """
    Función de enrutamiento de la arista condicional.

    Lee `perfil_valido` del estado y devuelve el nombre del siguiente
    nodo. Si el perfil no es válido, termina el grafo (END).
    """
    if state["perfil_valido"]:
        return "seleccionar_universo"
    return "informar_error"


def construir_grafo(kb):
    """
    Construye y compila el grafo de orquestación.

    Parameters
    ----------
    kb : BaseConocimiento
        Base de conocimiento para el nodo explicador. Se inyecta aquí
        mediante un cierre (partial), ya que los nodos solo reciben el
        estado.

    Returns
    -------
    Grafo compilado, listo para invocar con .invoke(estado_inicial).
    """
    
    # 1. Crear el grafo con el tipo de estado.
    grafo = StateGraph(PortfolioState)
    
    # 2. Registrar los nodos. El explicador necesita la kb: la inyectamos
    # con partial, que "fija" ese arguemnto dejando solo el estado.
    grafo.add_node("validar_perfil", nodo_validar_perfil)
    grafo.add_node("seleccionar_universo", nodo_seleccionar_universo)
    grafo.add_node("generar_views", nodo_generar_views)
    grafo.add_node("optimizar", nodo_optimizar)
    grafo.add_node("explicar", partial(nodo_explicar, kb=kb))
    grafo.add_node("informar_error", nodo_informar_error)
    
    # 3. Definir el punto de entrada-
    grafo.set_entry_point("validar_perfil")

    # 4. Arista CONDICIONAL: tras validar, decidir el camino-
    grafo.add_conditional_edges(
        "validar_perfil",
        _decidir_tras_validar,
        {
            "seleccionar_universo": "seleccionar_universo",
            "informar_error": "informar_error"
        }
    )
    
    # 5. Aristas normales: el resto del flujo es secuencial.
    grafo.add_edge("seleccionar_universo", "generar_views")
    grafo.add_edge("generar_views", "optimizar")
    grafo.add_edge("optimizar", "explicar")
    grafo.add_edge("explicar", END)
    grafo.add_edge("informar_error", END)
    
    # 6. Compilar: convierte la definición en un grafo ejecutable
    return grafo.compile()