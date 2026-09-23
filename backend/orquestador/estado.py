"""
Estado del grafo de orquestación.

Define PortfolioState: el objeto que viaja por todos los nodos del grafo,
acumulando la información que cada agente produce. Es la "memoria de
trabajo" compartida del sistema.

Cada nodo lee del estado lo que necesita y escribe su resultado. LangGraph
se encarga de propagar este estado de un nodo al siguiente, sustituyendo
el paso manual de variables del pipeline lineal.
"""

from typing import TypedDict, Optional

import pandas as pd

from agents.perfil import PerfilInversor
from agents.generador_views import ViewsGeneradas


class PortfolioState(TypedDict):
    """
    Estado compartido que viaja por el grafo de orquestación.

    Los campos se van rellenando conforme el estado pasa por los nodos:
    empieza con las entradas (perfil, universo, datos) y termina con la
    cartera y su explicación.
    """
    
    # --- Entradas (presentes desde el inicio) ---
    perfil: PerfilInversor
    universo: list[str]
    S: pd.DataFrame
    market_caps: dict[str, float]
    
    # --- Producido por el nodo de views ---
    views: Optional[ViewsGeneradas]
    
    # --- Producido por el nodo de views ---
    resultado: Optional[dict]
    
    # --- Producido por el nodo explicador ---
    explicacion: Optional[str]
    
    # --- Campo de control para las aristas condicionales ---
    perfil_valido: bool
    
    # --- Mensaje de error para el usuario (si el flujo se corta) ---
    mensaje_error: Optional[str]
