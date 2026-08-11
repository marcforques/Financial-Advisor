from orquestador.grafo import construir_grafo
from orquestador.estado import PortfolioState
from agents.perfil import PerfilInversor, NivelRiesgo, ObjetivoInversion
from rag.base_conocimiento import BaseConocimiento
from rag.corpus import DOCUMENTOS

kb = BaseConocimiento()
kb.añadir_documentos(DOCUMENTOS)
grafo = construir_grafo(kb)

perfil = PerfilInversor(
    nivel_riesgo=NivelRiesgo.MODERADO,
    horizonte_anios=20,
    capital=60000,
    objetivo=ObjetivoInversion.JUBILACION,
    matices=["Le preocupa la inflación"],
)

# Estado inicial: ahora el sistema selecciona universo, S y market_caps solo
estado_inicial: PortfolioState = {
    "perfil": perfil,
    "universo": [],          # lo rellena el nodo de selección
    "S": None,               # lo rellena el nodo de selección
    "market_caps": {},       # lo rellena el nodo de selección
    "views": None,
    "resultado": None,
    "explicacion": None,
    "perfil_valido": False,
    "mensaje_error": None,
}

print("Ejecutando el sistema completo (con selección de universo)...\n")
final = grafo.invoke(estado_inicial)

print("=" * 60)
print(f"Universo seleccionado ({len(final['universo'])} activos):")
print(f"  {final['universo']}")
print("\nCartera final:")
for activo, peso in final["resultado"]["pesos"].items():
    if peso > 0.001:
        m_region = ""
        try:
            from universo.catalogo import metadatos
            m_region = f" [{metadatos(activo)['region'].value}]"
        except Exception:
            pass
        print(f"  {activo}: {peso*100:.1f}%{m_region}")
print(f"\nSharpe: {final['resultado']['sharpe']:.2f}")