"""
Regla de decisión del rebalanceo.

Decide si merece la pena rebalancear una cartera, combinando dos filtros:

  1. Banda de tolerancia: la cartera debe haberse desviado del objetivo
     más que un umbral (si no, la desviación es ruido y no se toca).
  2. Tope de coste: el coste total (transacción + impuesto) debe ser
     razonable respecto al tamaño del rebalanceo (si corregir cuesta más
     de lo que aporta, no compensa).

Solo se rebalancea si se superan AMBOS filtros. Es código determinista:
el sistema recomienda, nunca ejecuta órdenes (marco de análisis
informativo, no asesoramiento ejecutado).
"""

from dataclasses import dataclass

from rebalanceo.costes import calcular_operaciones, coste_transaccion, ParametrosCoste
from rebalanceo.impuestos import impuesto_por_ventas


@dataclass
class ParametrosRebalanceo:
    """
    Parámetros de la decisión de rebalanceo.

    Attributes
    ----------
    banda_tolerancia : float
        Desviación máxima permitida por activo antes de rebalancear
        (0.05 = 5%). Por debajo, no se rebalancea.
    coste_maximo_pct : float
        Coste total máximo aceptable como fracción del importe a mover
        (0.30 = el coste no debe superar el 30% de lo que se rebalancea).
    """
    banda_tolerancia: float = 0.05
    coste_maximo_pct: float = 0.30
    

@dataclass
class ResultadoDecision:
    """
    Resultado de la decisión de rebalanceo.
    """
    rebalancear: bool
    motivo: str
    desviacion_maxima: float
    importe_a_mover: float
    coste_total: float
    coste_transaccion: float
    impuesto: float


def decidir_rebalanceo(
    pesos_actuales: dict[str, float],
    pesos_objetivo: dict[str, float],
    capital: float,
    precios_compra: dict[str, float],
    precios_actuales: dict[str, float],
    parametros: ParametrosRebalanceo = None,
    parametros_coste: ParametrosCoste = None
) -> ResultadoDecision:
    """
    Decide si rebalancear la cartera compensa.

    Parameters
    ----------
    pesos_actuales : dict[str, float]
        Pesos actuales (desviados) de la cartera.
    pesos_objetivo : dict[str, float]
        Pesos objetivo recomendados.
    capital : float
        Capital total de la cartera en euros.
    precios_compra : dict[str, float]
        Precio de adquisición por activo (para el impuesto).
    precios_actuales : dict[str, float]
        Precio actual por activo (para el impuesto).
    parametros : ParametrosRebalanceo, opcional
        Parámetros de la decisión (banda, tope de coste).
    parametros_coste : ParametrosCoste, opcional
        Parámetros de coste del broker.

    Returns
    -------
    ResultadoDecision
        La decisión con su motivo y los números que la respaldan.
    """
    
    if parametros is None:
        parametros = ParametrosRebalanceo()
    
    # -- Filtro 1: banda de tolerancia ---
    # Desviación de cada activo (cuánto se ha movido del objeto).
    todos = set(pesos_actuales) | set(pesos_objetivo)
    desviaciones = {
        a: abs(pesos_objetivo.get(a, 0.0) - pesos_actuales.get(a, 0.0)) for a in todos
    }
    desviacion_maxima = max(desviaciones.values()) if desviaciones else 0.0
    
    # Operaciones e importe a mover (lo necesitamos para el motivo aunque no se rebalancee).
    operaciones = calcular_operaciones(pesos_actuales, pesos_objetivo, capital)
    importe_a_mover = sum(abs(v) for v in operaciones.values()) / 2
    # (dividido entre 2: lo que se vende es iguala lo que se compra;
    #   el "importe movido" es una de las dos mitades)
    
    if desviacion_maxima < parametros.banda_tolerancia:
        return ResultadoDecision(
            rebalancear=False,
            motivo=(
                f"La desviación máxima ({desviacion_maxima*100:.1f}%) está "
                f"dentro de la banda de tolerancia "
                f"({parametros.banda_tolerancia*100:.0f}%). No compensa "
                f"rebalancear por movimientos pequeños."
            ),
            desviacion_maxima=desviacion_maxima,
            importe_a_mover=importe_a_mover,
            coste_total=0.0,
            coste_transaccion=0.0,
            impuesto=0.0
        )
        
    
    # --- Filtro 2: tope de coste ---
    # Coste de transacción.
    coste_trans = coste_transaccion(operaciones, parametros_coste)
    
    # Impuesto: solo sobre las ventas (importes negativos).
    ventas = {a: -v for a, v in operaciones.items() if v < 0}
    impuesto = impuesto_por_ventas(ventas, precios_compra, precios_actuales)
    
    coste_total = coste_trans + impuesto
    
    # ¿El coste es razonable respecto a lo que movemos?
    coste_relativo = coste_total / importe_a_mover if importe_a_mover > 0 else 0.0
    
    if coste_relativo > parametros.coste_maximo_pct:
        return ResultadoDecision(
            rebalancear=True,
            motivo=(
                f"El coste de rebalancear ({coste_total:.2f}€, "
                f"{coste_relativo*100:.1f}% de lo que se movería) supera el "
                f"límite aceptable ({parametros.coste_maximo_pct*100:.0f}%). "
                f"El impuesto sobre plusvalías lo hace poco rentable."
            ),
            desviacion_maxima=desviacion_maxima,
            importe_a_mover=importe_a_mover,
            coste_total=coste_total,
            coste_transaccion=coste_trans,
            impuesto=impuesto
        )

    # --- Pasa ambos filtros: rebalancear compensa ---
    return ResultadoDecision(
        rebalancear=True,
        motivo=(
            f"La desviación ({desviacion_maxima*100:.1f}%) supera la banda "
            f"y el coste ({coste_relativo*100:.1f}%) es aceptable. "
            f"Rebalancear compensa."
        ),
        desviacion_maxima=desviacion_maxima,
        importe_a_mover=importe_a_mover,
        coste_total=coste_total,
        coste_transaccion=coste_trans,
        impuesto=impuesto
    )