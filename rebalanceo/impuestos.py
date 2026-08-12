"""
Impuesto sobre plusvalías del ahorro (España).

Calcula el impuesto que genera vender activos con ganancia al rebalancear.
En España, las ganancias patrimoniales tributan en la base del ahorro con
una escala progresiva por tramos. El impuesto se aplica SOLO sobre la
ganancia realizada (precio de venta - precio de compra), no sobre el
importe total vendido.

Es la pieza que hace el sistema específico para un inversor español y, a
menudo, el mayor coste de rebalancear (mayor que las comisiones).
"""

# Escala del ahorro España 2024: lista de (límite_superior, tipo).
# El último tramo usa float('inf') como límite.

_TRAMOS_AHORRO = [
    (6_000.0, 0.19),
    (50_000.0, 0.21),
    (200_000.0, 0.23),
    (300_000.0, 0.27),
    (float("inf"), 0.28),
]


def impuesto_plusvalia(ganancia: float) -> float:
    """
    Calcula el impuesto sobre una ganancia patrimonial (escala España).

    Aplica la escala progresiva por tramos: cada porción de la ganancia
    tributa al tipo de su tramo. Una ganancia de 0 o negativa (pérdida) no
    genera impuesto.

    Parameters
    ----------
    ganancia : float
        Ganancia patrimonial realizada en euros.

    Returns
    -------
    float
        Impuesto a pagar en euros.
    """
    
    if ganancia <= 0:
        return 0.0
    
    impuesto = 0.0
    limite_anterior = 0.0
    
    for limite, tipo in _TRAMOS_AHORRO:
        if ganancia <= limite_anterior:
            break
        # Porción de la ganancia que cae en este tramo.
        porcion = min(ganancia, limite) - limite_anterior
        impuesto += porcion * tipo
        limite_anterior = limite

    return impuesto


def impuesto_por_ventas(
    ventas: dict[str, float],
    precios_compra: dict[str, float],
    precios_actuales: dict[str, float]
) -> float:
    """
    Calcula el impuesto total de un conjunto de ventas al rebalancear.

    Para cada venta, estima la ganancia realizada según la diferencia entre
    el precio actual y el de compra, y aplica la escala. Las ventas de
    activos en pérdida no generan impuesto (y en la práctica compensarían
    ganancias, pero eso es un refinamiento futuro).

    Parameters
    ----------
    ventas : dict[str, float]
        Importe vendido por activo en euros (valores positivos).
    precios_compra : dict[str, float]
        Precio medio de adquisición por activo.
    precios_actuales : dict[str, float]
        Precio actual por activo.

    Returns
    -------
    float
        Impuesto total a pagar por las ventas en euros.
    """
    ganancia_total = 0.0
    
    for activo, importe_vendido in ventas.items():
        precio_compra = precios_compra.get(activo)
        precio_actual = precios_actuales.get(activo)
        
        if not precio_compra or not precio_actual or precio_compra <= 0:
            continue

        # Fracción de ganancia sobre el importe vendido.
        # Si compré a 80 y vale 100, la ganancia es (100-80)/100 = 20% del
        # importe vendido.
        fraccion_ganancia = (precio_actual - precio_compra) / precio_actual
        ganancia = importe_vendido * fraccion_ganancia
        
        if ganancia > 0:
            ganancia_total += ganancia
        
    return impuesto_plusvalia(ganancia_total)       
    