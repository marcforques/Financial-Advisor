"""
Costes de transacción del rebalanceo.

Calcula cuánto cuesta, en euros, pasar de una cartera actual a una cartera
objetivo. Cada activo que cambia de peso genera una operación (compra o
venta) sobre la que se aplican comisión y spread.

Es código puro y determinista. Los parámetros de coste (comisión, spread)
son configurables para adaptarse a distintos brokers.
"""

from dataclasses import dataclass

@dataclass
class ParametrosCoste:
    """
    Parámetros de coste de un broker.

    Attributes
    ----------
    comision_pct : float
        Comisión por operación como fracción del importe (0.001 = 0,1%).
    spread_pct : float
        Spread implícito como fracción del importe (0.0005 = 0,05%).
    comision_minima : float
        Comisión mínima por operación en euros (algunos brokers la aplican).
    """
    comision_pct: float = 0.001
    spread_pct: float = 0.0005
    comision_minima: float = 0.0
    
    
def calcular_operaciones(
    pesos_actuales: dict[str, float], 
    pesos_objetivo: dict[str, float],
    capital: float
    ) -> dict[str, float]:
    """
    Calcula las operaciones necesarias para ir de actual a objetivo.

    Para cada activo, la operación es la diferencia de peso multiplicada
    por el capital. Positiva = comprar; negativa = vender.

    Parameters
    ----------
    pesos_actuales : dict[str, float]
        Pesos actuales de la cartera (activo -> peso).
    pesos_objetivo : dict[str, float]
        Pesos objetivo recomendados.
    capital : float
        Capital total de la cartera en euros.

    Returns
    -------
    dict[str, float]
        Importe en euros a operar por activo (+ compra, - venta).
    """
    # Todos los activos que aparecen en cualquiera de las dos carteras.
    todos = set(pesos_actuales) | set(pesos_objetivo)
    
    operaciones = {}
    for activo in todos:
        peso_ahora = pesos_actuales.get(activo, 0.0)
        peso_destino = pesos_objetivo.get(activo, 0.0)
        cambio_pct = peso_destino - peso_ahora
        importe = cambio_pct * capital
        # Solo registramos operaciones no triviales (> 1 céntimo).
        if abs(importe) > 0.01:
            operaciones[activo] = importe

    return operaciones


def coste_transaccion(
    operaciones: dict[str, float],
    parametros: ParametrosCoste = None
) -> float:
    """
    Calcula el coste total de transacción de un conjunto de operaciones.

    Cada operación (compra o venta) paga comisión y spread sobre su importe
    absoluto. La comisión respeta un mínimo por operación si se define.

    Parameters
    ----------
    operaciones : dict[str, float]
        Importe a operar por activo (+ compra, - venta).
    parametros : ParametrosCoste, opcional
        Parámetros de coste del broker. Si None, usa los por defecto.

    Returns
    -------
    float
        Coste total de transacción en euros.
    """
    if parametros is None:
        parametros = ParametrosCoste()
        
    coste_total = 0.0
    for activo, importe in operaciones.items():
        importe_abs = abs(importe)
        # Comisión: porcentaje con mínimo.
        comision = max(importe_abs * parametros.comision_pct, parametros.comision_minima)
        
        # Spread. porcentaje del importe.
        spread = importe_abs * parametros.spread_pct
        coste_total += comision + spread
    
    return coste_total