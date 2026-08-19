from core.data import descargar_precios
from core.analysis import rentabilidades_esperadas, matriz_covarianzas
from core.optimizer import optimizar_concentrada
from universo.selector import seleccionar_universo, restricciones_completas
from agents.perfil import PerfilInversor, NivelRiesgo, ObjetivoInversion

perfil = PerfilInversor(nivel_riesgo=NivelRiesgo.AGRESIVO, horizonte_anios=10,
                        capital=10000, objetivo=ObjetivoInversion.CRECIMIENTO)

universo = seleccionar_universo(perfil)
precios = descargar_precios(universo, "2015-01-01", "2025-01-01")
mu = rentabilidades_esperadas(precios)
S = matriz_covarianzas(precios)
restr = restricciones_completas(perfil, list(S.index))

resultado = optimizar_concentrada(mu, S, restr, max_activos=6, umbral_minimo=0.05)

print(f"Cartera concentrada ({len(resultado['pesos'])} activos):")
for ticker, peso in sorted(resultado["pesos"].items(), key=lambda x: -x[1]):
    print(f"  {ticker}: {peso*100:.1f}%")
print(f"\nSharpe: {resultado['sharpe']:.2f}")
print(f"Rentabilidad: {resultado['rentabilidad']*100:.1f}%")
print(f"Volatilidad: {resultado['volatilidad']*100:.1f}%")