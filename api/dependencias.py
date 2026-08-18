"""
Dependencias compartidas de la API.

Contiene recursos que varios módulos de la API necesitan (como el grafo de
orquestación compilado y la base de conocimiento), en un módulo
independiente para evitar imports circulares entre main.py y los routers.

El grafo y la kb se construyen una sola vez (carga diferida) y se
reutilizan en todas las peticiones.
"""
from rag.base_conocimiento import BaseConocimiento
from rag.corpus import DOCUMENTOS
from orquestador.grafo import construir_grafo

_kb = None
_grafo = None


def _construir_kb():
    """
    Prepara la base de conocimiento una sola vez.
    """
    kb = BaseConocimiento()
    kb.añadir_documentos(DOCUMENTOS)
    return kb


def obtener_grafo():
    """
    Devuelve el grafo compilado, construyéndolo la primera vez.
    """
    global _kb, _grafo
    if _grafo is None:
    
        _kb = _construir_kb()
        _grafo = construir_grafo(_kb)
    return _grafo