from rebalanceo.decision import decidir_rebalanceo, ParametrosRebalanceo

precios_compra = {"SPY": 400.0, "AGG": 100.0, "GLD": 150.0}
precios_actuales = {"SPY": 500.0, "AGG": 98.0, "GLD": 180.0}
capital = 10000

print("=" * 60)
print("ESCENARIO 1: desviación pequeña (dentro de la banda)")
print("=" * 60)
# La cartera apenas se ha movido
actuales_1 = {"SPY": 0.47, "AGG": 0.34, "GLD": 0.19}
objetivo = {"SPY": 0.45, "AGG": 0.35, "GLD": 0.20}
r1 = decidir_rebalanceo(actuales_1, objetivo, capital, precios_compra, precios_actuales)
print(f"¿Rebalancear? {r1.rebalancear}")
print(f"Motivo: {r1.motivo}")

print("\n" + "=" * 60)
print("ESCENARIO 2: desviación grande (las acciones se dispararon)")
print("=" * 60)
# SPY subió mucho, la cartera está muy desviada
actuales_2 = {"SPY": 0.65, "AGG": 0.20, "GLD": 0.15}
r2 = decidir_rebalanceo(actuales_2, objetivo, capital, precios_compra, precios_actuales)
print(f"¿Rebalancear? {r2.rebalancear}")
print(f"Motivo: {r2.motivo}")
print(f"Desviación máxima: {r2.desviacion_maxima*100:.1f}%")
print(f"Importe a mover: {r2.importe_a_mover:.2f}€")
print(f"  Coste transacción: {r2.coste_transaccion:.2f}€")
print(f"  Impuesto: {r2.impuesto:.2f}€")
print(f"  Coste total: {r2.coste_total:.2f}€")