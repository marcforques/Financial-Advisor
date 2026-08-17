from api.modelos_cartera import Posicion, CarteraGuardada
from agents.perfil import NivelRiesgo, ObjetivoInversion

# Una cartera guardada (o introducida a mano por el usuario)
cartera = CarteraGuardada(
    usuario_id="usuario_prueba",
    nombre="Mi cartera de jubilación",
    posiciones=[
        Posicion(ticker="SPY", participaciones=12, precio_compra=400.0),
        Posicion(ticker="AGG", participaciones=30, precio_compra=100.0),
        Posicion(ticker="GLD", participaciones=8, precio_compra=150.0),
    ],
    nivel_riesgo=NivelRiesgo.MODERADO,
    horizonte_anios=20,
    objetivo=ObjetivoInversion.JUBILACION,
)

print(f"Cartera: {cartera.nombre}")
print(f"Capital invertido: {cartera.capital_invertido():.2f}€\n")

# Precios actuales (SPY subió, GLD subió, AGG bajó un poco)
precios_hoy = {"SPY": 500.0, "AGG": 98.0, "GLD": 180.0}

print("Posiciones:")
for p in cartera.posiciones:
    valor = p.valor(precios_hoy[p.ticker])
    ganancia = p.ganancia(precios_hoy[p.ticker])
    print(f"  {p.ticker}: {p.participaciones} part. × {precios_hoy[p.ticker]}€ = {valor:.0f}€ (ganancia: {ganancia:+.0f}€)")

print("\nPesos actuales (derivados del valor de mercado):")
for ticker, peso in cartera.pesos_actuales(precios_hoy).items():
    print(f"  {ticker}: {peso*100:.1f}%")