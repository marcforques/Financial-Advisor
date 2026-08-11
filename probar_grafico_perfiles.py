from core.data import descargar_precios
from core.analysis import rentabilidades_esperadas, matriz_covarianzas
from core.optimizer import optimizar_markowitz
from agents.perfil import PerfilInversor, NivelRiesgo, ObjetivoInversion
from agents.restricciones import generar_restricciones
from evaluacion.graficos import grafico_comparacion_perfiles

universo = ["SPY", "AGG", "GLD", "EEM"]
precios_train = descargar_precios(universo, "2015-01-01", "2020-01-01")
precios_test = descargar_precios(universo, "2020-01-01", "2025-01-01")

mu = rentabilidades_esperadas(precios_train)
S = matriz_covarianzas(precios_train)
orden = list(mu.index)

carteras = {}
for nombre, nivel in [
    ("Conservador", NivelRiesgo.CONSERVADOR),
    ("Moderado", NivelRiesgo.MODERADO),
    ("Agresivo", NivelRiesgo.AGRESIVO),
]:
    perfil = PerfilInversor(
        nivel_riesgo=nivel, horizonte_anios=15, capital=50000,
        objetivo=ObjetivoInversion.CRECIMIENTO,
    )
    restr = generar_restricciones(perfil, orden)
    pesos = optimizar_markowitz(mu, S, restricciones=restr)["pesos"]
    carteras[nombre] = pesos

ruta = grafico_comparacion_perfiles(carteras, precios_test)
print(f"Gráfico guardado en: {ruta}")