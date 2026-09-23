"""
Pipeline de recomendación (versión secuencial manual).

Conecta la cadena completa: perfil -> views (LLM) -> Black-Litterman ->
cartera. Es la integración de la capa de IA con la capa cuantitativa.

En la Fase 5 esta orquestación se reescribirá con LangGraph como un grafo
formal con nodos y transiciones. Esta versión secuencial sirve para
validar que todas las piezas encajan antes de añadir esa complejidad.
"""

from agents.perfil import PerfilInversor
from agents.generador_views import generar_views
from agents.restricciones import generar_restricciones
from core.optimizer import optimizar_black_litterman, rentabilidades_equilibrio, optimizar_markowitz


def views_a_diccionario(views_generadas) -> dict[str, float]:
    """
    Convierte las views del LLM al formato que espera el optimizador.

    El LLM produce objetos View (activo, rentabilidad, justificación).
    Black-Litterman espera un diccionario {activo: rentabilidad}.

    Parameters
    ----------
    views_generadas : ViewsGeneradas
        Salida del agente generador de views.

    Returns
    -------
    dict[str, float]
        Views en formato {activo: rentabilidad_esperada}.
    """
    return {v.activo: v.rentabilidad_esperada for v in views_generadas.views}


def recomendar_cartera(perfil: PerfilInversor, universo: list[str], S, market_caps: dict[str, float]) -> dict:
    """
    Ejecuta la cadena completa y devuelve la cartera recomendada.

    Flujo:
      1. El agente de views traduce el perfil en inclinaciones (LLM).
      2. Las restricciones se generan desde el perfil (código).
      3. Black-Litterman combina views + equilibrio y optimiza.

    Parameters
    ----------
    perfil : PerfilInversor
        Perfil completo del inversor.
    universo : list[str]
        Tickers disponibles.
    S : pd.DataFrame
        Matriz de covarianzas.
    market_caps : dict[str, float]
        Capitalizaciones para el prior de equilibrio.

    Returns
    -------
    dict
        Resultado con pesos, métricas, posterior y las views usadas
        (con sus justificaciones, para poder explicar la cartera).
    """
    
    # 1. Generar views desde el perfil (LLM razona)
    views_generadas = generar_views(perfil, universo)
    views_dict = views_a_diccionario(views_generadas)
    
    # 2. Generar restricciones desde el perfil (código determinista)
    orden_canonico = list(S.index)
    restricciones = generar_restricciones(perfil, orden_canonico)
    
    # 3. Optimizazr con Black-Litterman
    #   Si no hay views, usamos un diccionario como view neutra mínima
    #   para que el modelo funcione (Black-Litterman necesita al menos una)
    if not views_dict:
        # Sin views la cartera será esencialmente el equilibrio de mercado.
        prior = rentabilidades_equilibrio(market_caps, S)
        resultado = optimizar_markowitz(prior, S, restricciones=restricciones)
        resultado["posterior"] = dict(prior)
    else:
        resultado = optimizar_black_litterman(S, market_caps, views_dict, restricciones=restricciones)
        
    # Adjuntamos las views con justificación para poder explicar la cartera
    resultado["views_usadas"] = [
        {"activo": v.activo, "justificacion": v.justificacion}
        for v in views_generadas.views
    ]
    
    return resultado
