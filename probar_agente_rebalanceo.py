from rebalanceo.agente import recomendar_rebalanceo

precios_compra = {"SPY": 400.0, "AGG": 100.0, "GLD": 150.0}
precios_actuales = {"SPY": 500.0, "AGG": 98.0, "GLD": 180.0}
capital = 10000

# Cartera muy desviada (SPY se disparó)
actuales = {"SPY": 0.65, "AGG": 0.20, "GLD": 0.15}
objetivo = {"SPY": 0.45, "AGG": 0.35, "GLD": 0.20}

rec = recomendar_rebalanceo(actuales, objetivo, capital, precios_compra, precios_actuales)

print("=" * 60)
print("RECOMENDACIÓN DE REBALANCEO")
print("=" * 60)
print(f"\n¿Rebalancear? {'SÍ' if rec.rebalancear else 'NO'}")
print(f"\nMotivo: {rec.motivo}")

if rec.rebalancear:
    print(f"\nPlan de operaciones:")
    for op in rec.plan:
        print(f"  {op.accion} {op.importe:.2f}€ de {op.activo}")
    print(f"\nCoste total del rebalanceo: {rec.decision.coste_total:.2f}€")
    print(f"  (transacción: {rec.decision.coste_transaccion:.2f}€ + "
          f"impuesto: {rec.decision.impuesto:.2f}€)")