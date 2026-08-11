from universo.catalogo import CATALOGO, tickers_catalogo, metadatos

print(f"Catálogo: {len(CATALOGO)} activos\n")

print("Todos los tickers:", tickers_catalogo())

print("\nActivos por región:")
from collections import defaultdict
por_region = defaultdict(list)
for a in CATALOGO:
    por_region[a["region"].value].append(a["ticker"])
for region, tickers in por_region.items():
    print(f"  {region}: {tickers}")

print("\nMetadatos de QQQ:")
for k, v in metadatos("QQQ").items():
    valor = v.value if hasattr(v, "value") else v
    print(f"  {k}: {valor}")