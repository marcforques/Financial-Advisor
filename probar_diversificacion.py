from agents.perfil import PerfilInversor, NivelRiesgo, ObjetivoInversion
from universo.diversificacion import restricciones_diversificacion
from universo.catalogo import metadatos

# Universo con el problema clásico: 3 activos muy EEUU + algo diversificador
activos = ["SPY", "QQQ", "URTH", "IEUR", "AGG", "GLD"]

print("Universo de prueba y sus regiones:")
for t in activos:
    m = metadatos(t)
    print(f"  {t}: región={m['region'].value}, sector={m['sector'].value}")

perfil = PerfilInversor(
    nivel_riesgo=NivelRiesgo.MODERADO, horizonte_anios=15,
    capital=50000, objetivo=ObjetivoInversion.CRECIMIENTO,
)

restr = restricciones_diversificacion(perfil, activos)
print(f"\nSe generaron {len(restr)} restricciones de diversificación.")

# Verificamos que una cartera concentrada en EEUU las VIOLA
import numpy as np
# 80% en los 3 activos EEUU/global (SPY, QQQ, URTH), 20% resto
pesos_concentrados = np.array([0.35, 0.30, 0.15, 0.05, 0.10, 0.05])
print(f"\nCartera concentrada: SPY=35%, QQQ=30%, URTH=15% (=80% muy EEUU)")

# Comprobamos la restricción de región EEUU
from universo.catalogo import Region
idx_eeuu = [i for i, t in enumerate(activos) if metadatos(t)["region"] == Region.EEUU]
suma_eeuu = sum(pesos_concentrados[i] for i in idx_eeuu)
print(f"Peso en EEUU (SPY+QQQ): {suma_eeuu*100:.0f}% — tope moderado: 55%")
print(f"¿Viola la restricción? {'SÍ' if suma_eeuu > 0.55 else 'NO'}")