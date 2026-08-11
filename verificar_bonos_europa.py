import yfinance as yf

# Candidatos de bonos europeos/globales con sufijo de bolsa.
# .AS=Ámsterdam, .L=Londres, .DE=Alemania, .MI=Milán
candidatos = {
    "IEAG.AS": "iShares Euro Aggregate Bond (Ámsterdam)",
    "IEAG.L": "iShares Euro Aggregate Bond (Londres)",
    "IEGA.AS": "iShares Core Euro Govt Bond (Ámsterdam)",
    "IBGL.AS": "iShares Euro Govt Bond largo plazo",
    "SEGA.L": "iShares Euro Govt Bond (Londres)",
    "VETY.DE": "Vanguard EUR Eurozone Govt Bond (Alemania)",
    "VAGF.L": "Vanguard Global Aggregate Bond hedged (Londres)",
    "AGGH.MI": "iShares Global Aggregate Bond hedged (Milán)",
    "EUNA.DE": "iShares Euro Aggregate Bond (Alemania)",
    "IBCI.DE": "iShares Euro Inflation Linked Govt Bond",
}

print("Verificando bonos europeos/globales...\n")
validos = []
for ticker, nombre in candidatos.items():
    try:
        d = yf.download(ticker, start="2020-01-01", end="2020-03-01",
                        progress=False, auto_adjust=True)
        if d.empty:
            print(f"  ✗ {ticker}: sin datos — {nombre}")
        else:
            print(f"  ✓ {ticker}: OK ({len(d)} días) — {nombre}")
            validos.append(ticker)
    except Exception as e:
        print(f"  ✗ {ticker}: error — {nombre}")

print(f"\nVálidos: {validos}")