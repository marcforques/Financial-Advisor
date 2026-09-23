"""
Límites de composición de cartera por nivel de riesgo.

Única fuente de verdad de los topes que dependen del perfil: máximo por
activo individual, máximo por región y máximo por sector. Antes estaban
repetidos (o, en el caso del máximo por activo durante la concentración,
sustituidos por un valor plano común) en distintos puntos del pipeline:
la generación de restricciones (universo/selector.py), la diversificación
(universo/diversificacion.py) y la concentración final de la cartera
(orquestador/nodos.py -> core.optimizer.concentrar_cartera). Centralizarlos
aquí garantiza que todas las fases apliquen siempre el mismo tope para un
mismo perfil.
"""

from agents.perfil import NivelRiesgo

# Máximo peso de un activo individual. Evita que una sola posición
# acapare la cartera, incluso dentro del cupo de su propia clase.
MAX_POR_ACTIVO = {
    NivelRiesgo.CONSERVADOR: 0.25,
    NivelRiesgo.MODERADO: 0.30,
    NivelRiesgo.AGRESIVO: 0.40,
}

# Máximo peso agregado por región. Un conservador debe estar MÁS
# diversificado geográficamente (topes más bajos) que un agresivo.
MAX_POR_REGION = {
    NivelRiesgo.CONSERVADOR: 0.45,
    NivelRiesgo.MODERADO: 0.55,
    NivelRiesgo.AGRESIVO: 0.70,
}

# Máximo peso agregado por sector concreto (no aplica a "amplio"/"na").
MAX_POR_SECTOR = {
    NivelRiesgo.CONSERVADOR: 0.20,
    NivelRiesgo.MODERADO: 0.30,
    NivelRiesgo.AGRESIVO: 0.40,
}
