"""
Nodos del grafo de orquestación.

Cada nodo envuelve a un agente existente de la Fase 4. El patrón es
siempre el mismo: lee del estado lo que necesita, llama al agente, y
devuelve un diccionario con los campos del estado que ha actualizado.

IMPORTANTE: los agentes NO se reescriben. Estos nodos son adaptadores
finos que conectan los agentes al grafo. Toda la lógica sigue viviendo
en los módulos de agents/ y core/.
"""
import pandas as pd

from agents.generador_views import generar_views
from agents.explicador import explicar_cartera
from agents.pipeline import views_a_diccionario
from core.optimizer import optimizar_black_litterman, rentabilidades_equilibrio, optimizar_markowitz
from orquestador.estado import PortfolioState
from universo.selector import seleccionar_universo, restricciones_completas
from core.data import descargar_precios
from core.analysis import matriz_covarianzas


def nodo_validar_perfil(state: PortfolioState) -> dict:
    """
    Comprueba que el perfil es válido antes de seguir.

    Escribe en `perfil_valido` el resultado de la validación, que la
    arista condicional usará para decidir el flujo. Como el perfil ya es
    un objeto Pydantic validado, aquí comprobamos coherencia adicional:
    que el universo no esté vacío y el capital sea razonable.
    """
    perfil = state["perfil"]
    
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
    Optimiza la cartera con Black-Litterman y las restricciones, y la
    reduce a una cartera concentrada y operativa.
    """
    from core.optimizer import concentrar_cartera

    perfil = state["perfil"]
    S = state["S"]
    market_caps = state["market_caps"]
    views = state["views"]

    orden_canonico = list(S.index)
    restricciones = restricciones_completas(perfil, orden_canonico)

    views_dict = views_a_diccionario(views) if views else {}

    if not views_dict:
        prior = rentabilidades_equilibrio(market_caps, S)
        resultado = optimizar_markowitz(prior, S, restricciones=restricciones)
        resultado["posterior"] = dict(prior)
        mu_usado = prior
    else:
        resultado = optimizar_black_litterman(S, market_caps, views_dict, restricciones=restricciones)
        # El posterior viene como dict en el resultado; lo pasamos a Series.
        mu_usado = pd.Series(resultado["posterior"])

    # Reducir a cartera concentrada y operativa.
    resultado = concentrar_cartera(
        resultado, mu_usado, S,
        max_activos=7, umbral_minimo=0.04, max_por_activo=0.35,
    )

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


def nodo_seleccionar_universo(state: PortfolioState) -> dict:
    """
    Selecciona el universo de activos adecuado para el perfil.

    Primera etapa del flujo real: en vez de recibir tickers fijos, el
    sistema elige del catálogo los activos apropiados al perfil, descarga
    sus precios y calcula la matriz de covarianzas. Escribe en el estado
    el universo, S y los market_caps.
    """
    perfil = state["perfil"]
    
    # Seleccionar universo del catálogo según el perfil.
    universo = seleccionar_universo(perfil)
    
    # Descargar precios y calcular covarianzas.
    precios = descargar_precios(universo, "2015-01-01", "2025-01-01")
    
    # El universo real es el de las columnas que se descargaron bien.
    universo_real = list(precios.columns)
    S = matriz_covarianzas(precios)
    
    # Market caps proxy: iguales para todos (simplificación).
    # En un sistema real vendrían del AUM de cada ETF.
    market_caps = {t: 1e9 for t in universo_real}
    
    # Verificar que el universo seleccionado permite diversificar.
    if len(universo_real) < 2:
        return {
            "universo": universo_real,
            "S": S,
            "market_caps": market_caps,
            "perfil_valido": False,
            "mensaje_error": (
                "El universo seleccionado para tu perfil es insuficiente "
                "para construir una cartera diversificada."
            )
        }
    
    return {
        "universo": universo_real,
        "S": S,
        "market_caps": market_caps
    }    