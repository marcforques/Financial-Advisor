"""
Catálogo de activos con metadatos.

El universo de inversión deja de ser una lista de tickers para ser una
tabla donde cada activo se describe por sus características: clase, región,
sector, coste y nivel de riesgo. Estos metadatos permiten dos cosas:
  - filtrar por adecuación al perfil (no mostrar cripto a un conservador),
  - razonar sobre diversificación real (evitar solapamiento por región).

En un sistema en producción este catálogo vendría de una base de datos o
un proveedor de datos. Aquí es un catálogo curado, suficiente para
demostrar la lógica de selección.

MIGRACIÓN A UCITS (2026-09-16): el catálogo usaba ETFs domiciliados en
EEUU (SPY, QQQ, EEM...). Para un inversor minorista de la UE, un bróker
sujeto a MiFID II no puede distribuir ETFs no-UCITS sin el KID de PRIIPs,
así que se ha sustituido cada activo por su equivalente UCITS (mismo
Clase/Region/Sector/NivelRiesgoActivo, misma exposición del índice),
normalmente domiciliado en Irlanda o Luxemburgo y cotizado en Xetra (.DE),
Euronext Amsterdam (.AS) o Londres (.L). Todos los tickers UCITS se han
verificado descargables vía yfinance (precio e histórico) el 2026-09-16.

El campo 'aum' es el patrimonio gestionado del fondo, usado como proxy
de capitalización de mercado para el prior de equilibrio de Black-Litterman
(a mayor AUM, mayor peso de equilibrio). Se guarda aquí como dato estático:
el prior de equilibrio no debe depender de tener red disponible en tiempo
de ejecución, ni fluctuar entre ejecuciones sucesivas del mismo perfil.
Fuente por activo (revisar el comentario de cada bloque):
  - "yfinance": Ticker.info['totalAssets'] de ese mismo ticker UCITS.
  - "justETF": el ticker UCITS no publica 'totalAssets' en yfinance; se
    tomó el AUM del factsheet de justETF.com (mismo ISIN) el 2026-09-16
    y se convirtió de EUR a USD al tipo EURUSD=X de esa fecha (1 EUR ≈
    1,1545 USD, vía yfinance).
  - "estimado, verificar": ni yfinance ni justETF devolvieron un AUM
    fiable para ese ticker concreto; se ha dejado una cifra orientativa
    y debe confirmarse contra el factsheet del emisor antes de citarla
    en la memoria.
IEGA.AS no publica AUM en Yahoo Finance bajo ese listado; se usó el valor
de la misma cotización en Londres (IEGA.L), mismo fondo y mismo ISIN.

El TER de cada UCITS se ha tomado de yfinance (Ticker.info['netExpenseRatio'])
cuando estaba disponible, o si no de justETF/Yahoo Finance (página web,
campo "Expense Ratio (net)"); ambas fuentes se cruzaron cuando fue posible
y coincidieron. Donde ninguna fuente en vivo lo confirmó, se ha usado el
TER publicado conocido del folleto/KID del fondo y se marca "verificar".
"""

from enum import Enum


class Clase(str, Enum):
    RENTA_VARIABLE = "renta_variable"
    BONOS = "bonos"
    MATERIAS_PRIMAS = "materias_primas"


class Region(str, Enum):
    EEUU = "eeuu"
    EUROPA = "europa"
    EMERGENTES = "emergentes"
    GLOBAL = "global"
    ASIA_PACIFICO = "asia_pacifico"
    NA = "no_aplica"

class Sector(str, Enum):
    AMPLIO = "amplio"          # índice general, no sectorial
    TECNOLOGIA = "tecnologia"
    SALUD = "salud"
    ENERGIA = "energia"
    FINANCIERO = "financiero"
    INMOBILIARIO = "inmobiliario"
    NA = "no_aplica"           # bonos, materias primas

class NivelRiesgoActivo(str, Enum):
    BAJO = "bajo"
    MEDIO = "medio"
    ALTO = "alto"


# Cada activo es un dict con sus metadatos.
# 'riesgo' indica qué perfiles pueden tenerlo.
# 'aum' es el patrimonio gestionado en USD (ver nota de módulo sobre fuentes).
CATALOGO = [
    # ═══ RENTA VARIABLE — EEUU ═══
    # SPY -> Vanguard S&P 500 UCITS ETF (USD Dist), IE00B3XXRP09. TER y AUM: yfinance.
    {"ticker": "VUSA.AS", "nombre": "S&P 500", "clase": Clase.RENTA_VARIABLE,
     "region": Region.EEUU, "sector": Sector.AMPLIO, "riesgo": NivelRiesgoActivo.MEDIO, "ter": 0.07,
     "aum": 89_225_781_248},
    # QQQ -> iShares NASDAQ-100 UCITS ETF (DE), DE000A0F5UF5. TER y AUM: yfinance (cruzado con justETF).
    {"ticker": "EXXT.DE", "nombre": "Nasdaq 100", "clase": Clase.RENTA_VARIABLE,
     "region": Region.EEUU, "sector": Sector.TECNOLOGIA, "riesgo": NivelRiesgoActivo.ALTO, "ter": 0.30,
     "aum": 6_184_098_304},
    # VTV -> iShares Edge MSCI USA Value Factor UCITS ETF (Acc). TER y AUM: yfinance.
    {"ticker": "IUVL.L", "nombre": "Value EEUU", "clase": Clase.RENTA_VARIABLE,
     "region": Region.EEUU, "sector": Sector.AMPLIO, "riesgo": NivelRiesgoActivo.MEDIO, "ter": 0.20,
     "aum": 3_897_677_312},
    # IWM -> Xtrackers Russell 2000 UCITS ETF 1C (mismo índice, Russell 2000). TER y AUM: yfinance.
    {"ticker": "XRS2.DE", "nombre": "Small caps EEUU", "clase": Clase.RENTA_VARIABLE,
     "region": Region.EEUU, "sector": Sector.AMPLIO, "riesgo": NivelRiesgoActivo.ALTO, "ter": 0.30,
     "aum": 2_851_059_200},

    # ═══ RENTA VARIABLE — GLOBAL / DESARROLLADOS ═══
    # URTH -> Vanguard FTSE Developed World UCITS ETF (Acc). TER y AUM: yfinance.
    {"ticker": "VHVE.L", "nombre": "MSCI World", "clase": Clase.RENTA_VARIABLE,
     "region": Region.GLOBAL, "sector": Sector.AMPLIO, "riesgo": NivelRiesgoActivo.MEDIO, "ter": 0.12,
     "aum": 11_707_333_632},
    # VEA -> Xtrackers MSCI World ex USA UCITS ETF 1C. TER y AUM: yfinance.
    # AVISO: categoría "World ex-USA" UCITS es reciente; histórico de precio disponible
    # solo desde 2024-03 (~2,5 años) frente a los >15 años del VEA original. Insuficiente
    # para un backtest de largo plazo; valorar excluirlo del backtest o documentarlo como
    # limitación de datos en la memoria.
    {"ticker": "EXUS.DE", "nombre": "Desarrollados ex-EEUU", "clase": Clase.RENTA_VARIABLE,
     "region": Region.GLOBAL, "sector": Sector.AMPLIO, "riesgo": NivelRiesgoActivo.MEDIO, "ter": 0.15,
     "aum": 8_192_445_440},

    # ═══ RENTA VARIABLE — EUROPA ═══
    # IEUR -> iShares Core MSCI Europe UCITS ETF (Acc). TER y AUM: yfinance.
    {"ticker": "IMAE.AS", "nombre": "Europa amplio", "clase": Clase.RENTA_VARIABLE,
     "region": Region.EUROPA, "sector": Sector.AMPLIO, "riesgo": NivelRiesgoActivo.MEDIO, "ter": 0.20,
     "aum": 16_135_584_768},
    # EZU -> iShares Core MSCI EMU UCITS ETF (Acc), IE00B53QG562. TER: yfinance.
    # AUM: justETF (EUR 6.115M) x EURUSD 2026-09-16 (1,1545).
    {"ticker": "SXR7.DE", "nombre": "Eurozona", "clase": Clase.RENTA_VARIABLE,
     "region": Region.EUROPA, "sector": Sector.AMPLIO, "riesgo": NivelRiesgoActivo.MEDIO, "ter": 0.12,
     "aum": 7_059_767_500},

    # ═══ RENTA VARIABLE — EMERGENTES ═══
    # EEM -> Xtrackers MSCI Emerging Markets UCITS ETF 1C. TER y AUM: yfinance.
    {"ticker": "XMME.DE", "nombre": "Emergentes amplio", "clase": Clase.RENTA_VARIABLE,
     "region": Region.EMERGENTES, "sector": Sector.AMPLIO, "riesgo": NivelRiesgoActivo.ALTO, "ter": 0.18,
     "aum": 15_064_839_168},
    # VWO -> Vanguard FTSE Emerging Markets UCITS ETF (Dist). TER y AUM: yfinance.
    {"ticker": "VFEM.L", "nombre": "Emergentes (Vanguard)", "clase": Clase.RENTA_VARIABLE,
     "region": Region.EMERGENTES, "sector": Sector.AMPLIO, "riesgo": NivelRiesgoActivo.ALTO, "ter": 0.17,
     "aum": 6_080_379_392},

    # ═══ RENTA VARIABLE — ASIA-PACÍFICO ═══
    # EWJ -> iShares MSCI Japan UCITS ETF (Dist). TER y AUM: yfinance.
    {"ticker": "IJPN.L", "nombre": "Japón", "clase": Clase.RENTA_VARIABLE,
     "region": Region.ASIA_PACIFICO, "sector": Sector.AMPLIO, "riesgo": NivelRiesgoActivo.MEDIO, "ter": 0.59,
     "aum": 5_092_681_728},
    # AAXJ -> Amundi MSCI AC Asia Ex Japan UCITS ETF (Acc). TER y AUM: yfinance.
    {"ticker": "APEX.L", "nombre": "Asia ex-Japón", "clase": Clase.RENTA_VARIABLE,
     "region": Region.ASIA_PACIFICO, "sector": Sector.AMPLIO, "riesgo": NivelRiesgoActivo.ALTO, "ter": 0.50,
     "aum": 398_192_512},

    # ═══ RENTA VARIABLE — SECTORIALES ═══
    # XLK -> Xtrackers MSCI USA Information Technology UCITS ETF 1D. TER y AUM: yfinance.
    {"ticker": "XUTC.DE", "nombre": "Tecnología EEUU", "clase": Clase.RENTA_VARIABLE,
     "region": Region.EEUU, "sector": Sector.TECNOLOGIA, "riesgo": NivelRiesgoActivo.ALTO, "ter": 0.12,
     "aum": 2_715_670_272},
    # XLV -> Xtrackers MSCI USA Health Care UCITS ETF 1D. TER y AUM: yfinance.
    {"ticker": "XUHC.DE", "nombre": "Salud EEUU", "clase": Clase.RENTA_VARIABLE,
     "region": Region.EEUU, "sector": Sector.SALUD, "riesgo": NivelRiesgoActivo.MEDIO, "ter": 0.12,
     "aum": 959_815_424},
    # XLE -> Xtrackers MSCI USA Energy UCITS ETF 1D. TER y AUM: yfinance.
    {"ticker": "XUEN.DE", "nombre": "Energía EEUU", "clase": Clase.RENTA_VARIABLE,
     "region": Region.EEUU, "sector": Sector.ENERGIA, "riesgo": NivelRiesgoActivo.ALTO, "ter": 0.12,
     "aum": 139_599_040},
    # XLF -> Xtrackers MSCI USA Financials UCITS ETF 1D. TER y AUM: yfinance.
    {"ticker": "XUFN.DE", "nombre": "Financiero EEUU", "clase": Clase.RENTA_VARIABLE,
     "region": Region.EEUU, "sector": Sector.FINANCIERO, "riesgo": NivelRiesgoActivo.ALTO, "ter": 0.12,
     "aum": 1_044_070_400},

    # ═══ INMOBILIARIO (REITs) ═══
    # VNQ -> iShares US Property Yield UCITS ETF (Dist). TER y AUM: yfinance.
    {"ticker": "IUSP.AS", "nombre": "Inmobiliario EEUU", "clase": Clase.RENTA_VARIABLE,
     "region": Region.EEUU, "sector": Sector.INMOBILIARIO, "riesgo": NivelRiesgoActivo.MEDIO, "ter": 0.40,
     "aum": 674_074_688},

    # ═══ RENTA FIJA — EEUU ═══
    # AGG -> iShares US Aggregate Bond UCITS ETF (Dist). TER: yfinance.
    # AUM: estimado, verificar contra el factsheet de iShares antes de citarlo en la memoria.
    {"ticker": "SUAG.L", "nombre": "Bonos agregados EEUU", "clase": Clase.BONOS,
     "region": Region.EEUU, "sector": Sector.NA, "riesgo": NivelRiesgoActivo.BAJO, "ter": 0.25,
     "aum": 1_600_000_000},
    # TLT -> iShares $ Treasury Bond 20+yr UCITS ETF (Dist), IE00BSKRJZ44. TER: yfinance.
    # AUM: justETF (EUR 867M) x EURUSD 2026-09-16 (1,1545).
    {"ticker": "IDTL.L", "nombre": "Tesoro EEUU largo plazo", "clase": Clase.BONOS,
     "region": Region.EEUU, "sector": Sector.NA, "riesgo": NivelRiesgoActivo.MEDIO, "ter": 0.07,
     "aum": 1_000_951_500},
    # IEF -> iShares $ Treasury Bond 7-10yr UCITS ETF (Acc), IE00B3VWN518. TER: yfinance.
    # AUM: justETF (EUR 4.311M) x EURUSD 2026-09-16 (1,1545).
    {"ticker": "IDTM.L", "nombre": "Tesoro EEUU medio plazo", "clase": Clase.BONOS,
     "region": Region.EEUU, "sector": Sector.NA, "riesgo": NivelRiesgoActivo.BAJO, "ter": 0.07,
     "aum": 4_977_049_500},
    # LQD -> Xtrackers USD Corporate Bond UCITS ETF 1D. TER: yfinance.
    # AUM: estimado, verificar contra el factsheet de Xtrackers antes de citarlo en la memoria.
    {"ticker": "XDGU.DE", "nombre": "Bonos corporativos EEUU", "clase": Clase.BONOS,
     "region": Region.EEUU, "sector": Sector.NA, "riesgo": NivelRiesgoActivo.MEDIO, "ter": 0.12,
     "aum": 1_900_000_000},
    # TIP -> iShares $ TIPS UCITS ETF (Acc). TER: yfinance.
    # AUM: estimado, verificar contra el factsheet de iShares antes de citarlo en la memoria.
    {"ticker": "ITPS.L", "nombre": "Bonos ligados inflación EEUU", "clase": Clase.BONOS,
     "region": Region.EEUU, "sector": Sector.NA, "riesgo": NivelRiesgoActivo.BAJO, "ter": 0.10,
     "aum": 1_100_000_000},

    # ═══ RENTA FIJA — EUROPA (verificados, en EUR) ═══
    # Ya eran UCITS (domiciliados en Irlanda, cotizados en EUR) en el catálogo original;
    # no se sustituyen, solo se documenta la fuente de AUM en la nota de módulo.
    {"ticker": "IEAG.AS", "nombre": "Bonos agregados euro", "clase": Clase.BONOS,
     "region": Region.EUROPA, "sector": Sector.NA, "riesgo": NivelRiesgoActivo.BAJO, "ter": 0.25,
     "aum": 1_691_230_208},
    {"ticker": "IEGA.AS", "nombre": "Bonos gobierno euro", "clase": Clase.BONOS,
     "region": Region.EUROPA, "sector": Sector.NA, "riesgo": NivelRiesgoActivo.BAJO, "ter": 0.09,
     "aum": 2_149_573_376},
    {"ticker": "IBCI.DE", "nombre": "Bonos ligados inflación euro", "clase": Clase.BONOS,
     "region": Region.EUROPA, "sector": Sector.NA, "riesgo": NivelRiesgoActivo.BAJO, "ter": 0.09,
     "aum": 1_918_543_232},

    # ═══ RENTA FIJA — GLOBAL ═══
    # BNDX -> iShares Core Global Aggregate Bond UCITS ETF EUR Hedged (Acc), IE00BDBRDM35.
    # TER: yfinance, cruzado con justETF (coincide). AUM: justETF (EUR 2.509M) x EURUSD
    # 2026-09-16 (1,1545). Cobertura a EUR en vez de a USD: reduce el riesgo de divisa
    # del original BNDX (USD Hedged) para un inversor en euros, cambio de diseño razonable
    # para el perfil UE aunque no sea una réplica exacta del hedge de BNDX.
    {"ticker": "AGGH.AS", "nombre": "Bonos internacionales ex-EEUU", "clase": Clase.BONOS,
     "region": Region.GLOBAL, "sector": Sector.NA, "riesgo": NivelRiesgoActivo.BAJO, "ter": 0.10,
     "aum": 2_896_640_500},
    # EMB -> iShares J.P. Morgan $ EM Bond UCITS ETF (Dist), IE00B2NPKV68. TER: yfinance,
    # cruzado con justETF (coincide). AUM: justETF (EUR 3.623M) x EURUSD 2026-09-16 (1,1545).
    {"ticker": "IEMB.L", "nombre": "Bonos emergentes", "clase": Clase.BONOS,
     "region": Region.EMERGENTES, "sector": Sector.NA, "riesgo": NivelRiesgoActivo.ALTO, "ter": 0.45,
     "aum": 4_182_753_500},

    # ═══ MATERIAS PRIMAS ═══
    # GLD -> iShares Physical Gold ETC. TER: justETF. AUM: justETF (EUR 33.403M) x EURUSD
    # 2026-09-16 (1,1545).
    {"ticker": "SGLN.L", "nombre": "Oro", "clase": Clase.MATERIAS_PRIMAS,
     "region": Region.NA, "sector": Sector.NA, "riesgo": NivelRiesgoActivo.MEDIO, "ter": 0.12,
     "aum": 38_563_763_500},
    # SLV -> iShares Physical Silver ETC. TER: justETF. AUM: justETF (EUR 2.773M) x EURUSD
    # 2026-09-16 (1,1545).
    {"ticker": "SSLN.L", "nombre": "Plata", "clase": Clase.MATERIAS_PRIMAS,
     "region": Region.NA, "sector": Sector.NA, "riesgo": NivelRiesgoActivo.ALTO, "ter": 0.20,
     "aum": 3_201_428_500},
    # DBC -> iShares Diversified Commodity Swap UCITS ETF. TER y AUM: yfinance.
    {"ticker": "ICOM.L", "nombre": "Materias primas diversificadas", "clase": Clase.MATERIAS_PRIMAS,
     "region": Region.NA, "sector": Sector.NA, "riesgo": NivelRiesgoActivo.ALTO, "ter": 0.19,
     "aum": 2_370_721_024},
]


def tickers_catalogo() -> list[str]:
    """Devuelve la lista de todos los tickers del catálogo."""
    return [activo["ticker"] for activo in CATALOGO]


def metadatos(ticker: str) -> dict:
    """Devuelve los metadatos de un ticker concreto."""
    for activo in CATALOGO:
        if activo["ticker"] == ticker:
            return activo
    raise KeyError(f"Ticker '{ticker}' no está en el catálogo.")


def capitalizaciones_mercado(tickers: list[str]) -> dict[str, float]:
    """
    Devuelve el AUM (proxy de capitalización de mercado) de cada ticker,
    tal como está guardado en el catálogo, para usar como prior de
    equilibrio en Black-Litterman.
    """
    return {ticker: float(metadatos(ticker)["aum"]) for ticker in tickers}
