from core.data import descargar_precios
from core.analysis import rentabilidades_esperadas, matriz_covarianzas
from core.optimizer import optimizar_markowitz, optimizar_black_litterman
from evaluacion.graficos import grafico_evolucion_carteras

universo = ["SPY", "AGG", "GLD", "EEM"]
precios_train = descargar_precios(universo, "2015-01-01", "2020-01-01")
precios_test = descargar_precios(universo, "2020-01-01", "2025-01-01")

mu = rentabilidades_esperadas(precios_train)
S = matriz_covarianzas(precios_train)
market_caps = {"AGG": 100e9, "EEM": 20e9, "GLD": 60e9, "SPY": 400e9}

# Preparar las carteras (mismas que el ablation)
restr = [lambda w: w <= 0.40, lambda w: w >= 0.05]

carteras = {
    "Equiponderada": {a: 0.25 for a in universo},
    "Markowitz puro": optimizar_markowitz(mu, S)["pesos"],
    "Markowitz + perfil": optimizar_markowitz(mu, S, restricciones=restr)["pesos"],
    "Black-Litterman": optimizar_black_litterman(S, market_caps, {"GLD": 0.07}, restricciones=restr)["pesos"],
}

ruta = grafico_evolucion_carteras(carteras, precios_test)
print(f"Gráfico guardado en: {ruta}")
print("Ábrelo para ver la evolución de las carteras.")