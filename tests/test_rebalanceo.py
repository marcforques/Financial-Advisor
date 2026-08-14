"""
Tests del sistema de rebalanceo.

Blindan las tres capas: costes de transacción, impuesto sobre plusvalías
(escala España) y la regla de decisión (banda de tolerancia + tope de
coste). La lógica financiera debe ser correcta al céntimo.
"""
import pytest

from rebalanceo.costes import calcular_operaciones, coste_transaccion, ParametrosCoste
from rebalanceo.impuestos import impuesto_plusvalia, impuesto_por_ventas
from rebalanceo.decision import decidir_rebalanceo, ParametrosRebalanceo
from rebalanceo.agente import recomendar_rebalanceo


# ─────────── Costes de transacción ───────────
def test_calcular_operaciones_direccion():
    """
    Las operaciones deben tener el signo correcto (+ compra, - venta).
    """
    actuales = {"SPY": 0.60, "AGG": 0.40}
    objetivo = {"SPY": 0.45, "AGG": 0.55}
    ops = calcular_operaciones(actuales, objetivo, 10000)
    
    assert ops["SPY"] < 0
    assert ops["AGG"] > 0
    

def test_coste_transaccion_positivo():
    """
    El coste de transacción siempre es positivo.
    """
    ops = {"SPY": -1000.0, "AGG": 1000.0}
    coste = coste_transaccion(ops)
    assert coste > 0
    

def test_comision_minima_se_aplica():
    """
    Si la comisión porcentual es menor que el mínimo, se usa el mínimo.
    """
    ops = {"SPY": 10.0}
    params = ParametrosCoste(comision_pct=0.001, comision_minima=1.0)
    coste = coste_transaccion(ops, params)
    
    # La comisión porcentual sería 0.01€, pero el mínimo es 1€.
    assert coste >= 1.0
    
    
# ─────────── Impuesto sobre plusvalías ───────────
def test_impuesto_primer_tramo():
    """
    Una ganancia en el primer tramo tributa al 19%.
    """
    assert impuesto_plusvalia(1000) == pytest.approx(190.0)
    

def test_impuesto_progresivo():
    """
    Una ganancia que cruza tramos tributa progresivamente.
    """
    # 10.000€: 6.000 al 19% + 4.000 al 21% = 1140 + 840 = 1980
    assert impuesto_plusvalia(10000) == pytest.approx(1980.0)

    
def test_perdida_no_tributa():
    """
    Una pérdida (ganancia negativa) no genera impuesto.
    """
    assert impuesto_plusvalia(-5000) == 0.0
    

def test_impuesto_solo_sobre_ganancia():
    """
    El impuesto se calcula sobre la ganancia, no sobre lo vendido.
    """
    # Vendo 1000€ de algo comprado a 400, ahora a 500.
    # Ganancia = 1000 * (500-400)/500 = 200€. Impuesto = 200*0.19 = 38€.
    ventas = {"SPY": 1000.0}
    imp = impuesto_por_ventas(ventas, {"SPY": 400.0}, {"SPY": 500.0})      
    assert imp == pytest.approx(38.0)
    

# ─────────── Regla de decisión ───────────
def test_no_rebalancear_dentro_de_banda():
    """
    Desviación pequeña -> no rebalancear.
    """
    actuales = {"SPY": 0.47, "AGG": 0.53}
    objetivo = {"SPY": 0.45, "AGG": 0.55}
    r = decidir_rebalanceo(
        actuales, objetivo, 10000,
        {"SPY": 400.0, "AGG": 100.0}, {"SPY": 500.0, "AGG": 98.0}
    )
    assert r.rebalancear is False


def test_rebalancear_fuera_de_banda():
    """
    Desviación grande con coste aceptable -> rebalancear.
    """
    actuales = {"SPY": 0.65, "AGG": 0.35}
    objetivo = {"SPY": 0.45, "AGG": 0.55}
    r = decidir_rebalanceo(
        actuales, objetivo, 10000,
        {"SPY": 400.0, "AGG": 100.0}, {"SPY": 500.0, "AGG": 98.0}
    )
    assert r.rebalancear is True
    assert r.desviacion_maxima == pytest.approx(0.20)
    
    
def test_no_rebalancear_si_coste_excesivo():
    """
    Si el coste supera el tope, no se rebalancea aunque supere la banda.
    """
    actuales = {"SPY": 0.65, "AGG": 0.35}
    objetivo = {"SPY": 0.45, "AGG": 0.55}
    # Tope de coste muy bajo (1%): casi cualquier impuesto lo supera.
    params = ParametrosRebalanceo(banda_tolerancia=0.05, coste_maximo_pct=0.01)
    r = decidir_rebalanceo(
        actuales, objetivo, 10000,
        {"SPY": 400.0, "AGG": 100.0}, {"SPY": 500.0, "AGG": 98.0},
        parametros=params
    )
    assert r.rebalancear is False   


# ─────────── Agente completo ───────────
def test_agente_genera_plan_si_rebalancea():
    """
    Si se rebalancea, el plan no está vacío y tiene ventas y compras.
    """
    actuales = {"SPY": 0.65, "AGG": 0.35}
    objetivo = {"SPY": 0.45, "AGG": 0.55}
    rec = recomendar_rebalanceo(
        actuales, objetivo, 10000,
        {"SPY": 400.0, "AGG": 100.0}, {"SPY": 500.0, "AGG": 98.0},
    )
    assert rec.rebalancear is True
    assert len(rec.plan) > 0
    acciones = {op.accion for op in rec.plan}
    assert "VENDER" in acciones and "COMPRAR" in acciones


def test_agente_sin_plan_si_no_rebalancea():
    """
    Si no se rebalancea, el plan está vacío.
    """
    actuales = {"SPY": 0.47, "AGG": 0.53}
    objetivo = {"SPY": 0.45, "AGG": 0.55}
    rec = recomendar_rebalanceo(
        actuales, objetivo, 10000,
        {"SPY": 400.0, "AGG": 100.0}, {"SPY": 500.0, "AGG": 98.0}
    )
    assert rec.rebalancear is False
    assert rec.plan == []
      
    

    
    
    
