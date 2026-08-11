from agents.perfil import NivelRiesgo
from universo.seleccion import filtrar_por_perfil, resumen_seleccion

for nivel in [NivelRiesgo.CONSERVADOR, NivelRiesgo.MODERADO, NivelRiesgo.AGRESIVO]:
    print(f"\n{'='*50}")
    print(f"PERFIL: {nivel.value.upper()}")
    print('='*50)

    tickers = filtrar_por_perfil(nivel)
    resumen = resumen_seleccion(nivel)

    print(f"Activos admitidos: {resumen['n_seleccionados']} de 30")
    print(f"Descartados: {resumen['descartados']}")
    print(f"Por clase: {dict(resumen['por_clase'])}")
    print(f"Por región: {dict(resumen['por_region'])}")