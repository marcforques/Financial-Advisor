import yfinance as yf
from universo.catalogo import tickers_catalogo

tickers = tickers_catalogo()
print(f"Verificando {len(tickers)} tickers del catálogo...\n")

for ticker in tickers:
    try:
        datos = yf.download(ticker, start="2023-01-01", end="2023-02-01",
                            progress=False, auto_adjust=True)
        if datos.empty:
            print(f"  ✗ {ticker}: SIN DATOS (ticker no válido en yfinance)")
        else:
            print(f"  ✓ {ticker}: OK ({len(datos)} días)")
    except Exception as e:
        print(f"  ✗ {ticker}: ERROR - {e}")