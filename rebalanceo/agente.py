"""
Agente de rebalanceo.

Cara pública del paquete de rebalanceo. Une las piezas internas (costes,
impuestos, decisión) y produce una recomendación completa: si rebalancear
o no, por qué, y —si procede— el plan de operaciones concreto.

REGLA DE ORO: es código determinista. El agente RECOMIENDA un plan; nunca
ejecuta órdenes. La ejecución queda en manos del usuario, coherente con el
marco de análisis informativo (no asesoramiento ejecutado).
"""

from dataclasses import dataclass

from rebalanceo.costes import calcular_operaciones, ParametrosCoste
from rebalanceo.decision import decidir_rebalanceo, ParametrosRebalanceo, ResultadoDecision


@dataclass
class Operacion:
    """
    Una operación concreta del plan de rebalanceo.
    """
    activo: str
    accion: str     # "COMPRAR" o "VENDER"
    importe: float      # en euros, siempre positivo


@dataclass 
class RecomendacionRebalanceo:
    """
    Recomendación completa de rebalanceo para el usuario.
    """
    rebalancear: bool
    motivo: str
    decision: ResultadoDecision
    plan: list[Operacion]
    

def recomendar_rebalanceo(
    pesos_actuales: dict[str, float],
    pesos_objetivo: dict[str, float],
    capital: float,
    precios_compra: dict[str, float],
    precios_actuales: dict[str, float],
    parametros: ParametrosRebalanceo = None,
    parametros_coste: ParametrosCoste = None 
) -> RecomendacionRebalanceo:
    """
    Produce una recomendación completa de rebalanceo.

    Decide si rebalancear compensa y, si es así, genera el plan de
    operaciones concreto (qué comprar y vender, en euros).

    Parameters
    ----------
    (ver decidir_rebalanceo)

    Returns
    -------
    RecomendacionRebalanceo
        La recomendación con el plan de operaciones si procede.
    """
    
    # Decidir si compensa rebalancear
    decision = decidir_rebalanceo(
        pesos_actuales, pesos_objetivo, capital, precios_compra,
        precios_actuales, parametros, parametros_coste
        )

    # Si no compensa, devolvemos la recomendación sin plan.
    if not decision.rebalancear:
        return RecomendacionRebalanceo(
            rebalancear=False,
            motivo=decision.motivo,
            decision=decision,
            plan=[]
        )
    
    # Si compensa, generamos el plan de operaciones concreto.
    operaciones = calcular_operaciones(pesos_actuales, pesos_objetivo, capital)
    plan = []
    for activo, importe in operaciones.items():
        plan.append(Operacion(
            activo=activo, 
            accion="COMPRAR" if importe > 0 else "VENDER",
            importe=abs(importe)
        ))
        
    # Ordenamos: primero ventas, luego compras (lógica real: vendes para
    # tener liquidez con la que comprar).
    plan.sort(key=lambda op: op.accion, reverse=True)   # VENDER antes que COMPRAR
    
    return RecomendacionRebalanceo(
        rebalancear=True,
        motivo=decision.motivo,
        decision=decision,
        plan=plan
    )    