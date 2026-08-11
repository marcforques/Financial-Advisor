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
CATALOGO = [
    # ═══ RENTA VARIABLE — EEUU ═══
    {"ticker": "SPY", "nombre": "S&P 500", "clase": Clase.RENTA_VARIABLE,
     "region": Region.EEUU, "sector": Sector.AMPLIO, "riesgo": NivelRiesgoActivo.MEDIO, "ter": 0.09},
    {"ticker": "QQQ", "nombre": "Nasdaq 100", "clase": Clase.RENTA_VARIABLE,
     "region": Region.EEUU, "sector": Sector.TECNOLOGIA, "riesgo": NivelRiesgoActivo.ALTO, "ter": 0.20},
    {"ticker": "VTV", "nombre": "Value EEUU", "clase": Clase.RENTA_VARIABLE,
     "region": Region.EEUU, "sector": Sector.AMPLIO, "riesgo": NivelRiesgoActivo.MEDIO, "ter": 0.04},
    {"ticker": "IWM", "nombre": "Small caps EEUU", "clase": Clase.RENTA_VARIABLE,
     "region": Region.EEUU, "sector": Sector.AMPLIO, "riesgo": NivelRiesgoActivo.ALTO, "ter": 0.19},

    # ═══ RENTA VARIABLE — GLOBAL / DESARROLLADOS ═══
    {"ticker": "URTH", "nombre": "MSCI World", "clase": Clase.RENTA_VARIABLE,
     "region": Region.GLOBAL, "sector": Sector.AMPLIO, "riesgo": NivelRiesgoActivo.MEDIO, "ter": 0.24},
    {"ticker": "VEA", "nombre": "Desarrollados ex-EEUU", "clase": Clase.RENTA_VARIABLE,
     "region": Region.GLOBAL, "sector": Sector.AMPLIO, "riesgo": NivelRiesgoActivo.MEDIO, "ter": 0.03},
    
    # ═══ RENTA VARIABLE — EUROPA ═══
    {"ticker": "IEUR", "nombre": "Europa amplio", "clase": Clase.RENTA_VARIABLE,
     "region": Region.EUROPA, "sector": Sector.AMPLIO, "riesgo": NivelRiesgoActivo.MEDIO, "ter": 0.11},
    {"ticker": "EZU", "nombre": "Eurozona", "clase": Clase.RENTA_VARIABLE,
     "region": Region.EUROPA, "sector": Sector.AMPLIO, "riesgo": NivelRiesgoActivo.MEDIO, "ter": 0.51},

    # ═══ RENTA VARIABLE — EMERGENTES ═══
    {"ticker": "EEM", "nombre": "Emergentes amplio", "clase": Clase.RENTA_VARIABLE,
     "region": Region.EMERGENTES, "sector": Sector.AMPLIO, "riesgo": NivelRiesgoActivo.ALTO, "ter": 0.68},
    {"ticker": "VWO", "nombre": "Emergentes (Vanguard)", "clase": Clase.RENTA_VARIABLE,
     "region": Region.EMERGENTES, "sector": Sector.AMPLIO, "riesgo": NivelRiesgoActivo.ALTO, "ter": 0.08},

    # ═══ RENTA VARIABLE — ASIA-PACÍFICO ═══
    {"ticker": "EWJ", "nombre": "Japón", "clase": Clase.RENTA_VARIABLE,
     "region": Region.ASIA_PACIFICO, "sector": Sector.AMPLIO, "riesgo": NivelRiesgoActivo.MEDIO, "ter": 0.50},
    {"ticker": "AAXJ", "nombre": "Asia ex-Japón", "clase": Clase.RENTA_VARIABLE,
     "region": Region.ASIA_PACIFICO, "sector": Sector.AMPLIO, "riesgo": NivelRiesgoActivo.ALTO, "ter": 0.69},
    
    # ═══ RENTA VARIABLE — SECTORIALES ═══
    {"ticker": "XLK", "nombre": "Tecnología EEUU", "clase": Clase.RENTA_VARIABLE,
     "region": Region.EEUU, "sector": Sector.TECNOLOGIA, "riesgo": NivelRiesgoActivo.ALTO, "ter": 0.09},
    {"ticker": "XLV", "nombre": "Salud EEUU", "clase": Clase.RENTA_VARIABLE,
     "region": Region.EEUU, "sector": Sector.SALUD, "riesgo": NivelRiesgoActivo.MEDIO, "ter": 0.09},
    {"ticker": "XLE", "nombre": "Energía EEUU", "clase": Clase.RENTA_VARIABLE,
     "region": Region.EEUU, "sector": Sector.ENERGIA, "riesgo": NivelRiesgoActivo.ALTO, "ter": 0.09},
    {"ticker": "XLF", "nombre": "Financiero EEUU", "clase": Clase.RENTA_VARIABLE,
     "region": Region.EEUU, "sector": Sector.FINANCIERO, "riesgo": NivelRiesgoActivo.ALTO, "ter": 0.09},

    # ═══ INMOBILIARIO (REITs) ═══
    {"ticker": "VNQ", "nombre": "Inmobiliario EEUU", "clase": Clase.RENTA_VARIABLE,
     "region": Region.EEUU, "sector": Sector.INMOBILIARIO, "riesgo": NivelRiesgoActivo.MEDIO, "ter": 0.13},
    
    # ═══ RENTA FIJA — EEUU ═══
    {"ticker": "AGG", "nombre": "Bonos agregados EEUU", "clase": Clase.BONOS,
     "region": Region.EEUU, "sector": Sector.NA, "riesgo": NivelRiesgoActivo.BAJO, "ter": 0.03},
    {"ticker": "TLT", "nombre": "Tesoro EEUU largo plazo", "clase": Clase.BONOS,
     "region": Region.EEUU, "sector": Sector.NA, "riesgo": NivelRiesgoActivo.MEDIO, "ter": 0.15},
    {"ticker": "IEF", "nombre": "Tesoro EEUU medio plazo", "clase": Clase.BONOS,
     "region": Region.EEUU, "sector": Sector.NA, "riesgo": NivelRiesgoActivo.BAJO, "ter": 0.15},
    {"ticker": "LQD", "nombre": "Bonos corporativos EEUU", "clase": Clase.BONOS,
     "region": Region.EEUU, "sector": Sector.NA, "riesgo": NivelRiesgoActivo.MEDIO, "ter": 0.14},
    {"ticker": "TIP", "nombre": "Bonos ligados inflación EEUU", "clase": Clase.BONOS,
     "region": Region.EEUU, "sector": Sector.NA, "riesgo": NivelRiesgoActivo.BAJO, "ter": 0.19},

    # ═══ RENTA FIJA — EUROPA (verificados, en EUR) ═══
    {"ticker": "IEAG.AS", "nombre": "Bonos agregados euro", "clase": Clase.BONOS,
     "region": Region.EUROPA, "sector": Sector.NA, "riesgo": NivelRiesgoActivo.BAJO, "ter": 0.25},
    {"ticker": "IEGA.AS", "nombre": "Bonos gobierno euro", "clase": Clase.BONOS,
     "region": Region.EUROPA, "sector": Sector.NA, "riesgo": NivelRiesgoActivo.BAJO, "ter": 0.09},
    {"ticker": "IBCI.DE", "nombre": "Bonos ligados inflación euro", "clase": Clase.BONOS,
     "region": Region.EUROPA, "sector": Sector.NA, "riesgo": NivelRiesgoActivo.BAJO, "ter": 0.09},

    # ═══ RENTA FIJA — GLOBAL ═══
    {"ticker": "BNDX", "nombre": "Bonos internacionales ex-EEUU", "clase": Clase.BONOS,
     "region": Region.GLOBAL, "sector": Sector.NA, "riesgo": NivelRiesgoActivo.BAJO, "ter": 0.07},
    {"ticker": "EMB", "nombre": "Bonos emergentes", "clase": Clase.BONOS,
     "region": Region.EMERGENTES, "sector": Sector.NA, "riesgo": NivelRiesgoActivo.ALTO, "ter": 0.39},

    # ═══ MATERIAS PRIMAS ═══
    {"ticker": "GLD", "nombre": "Oro", "clase": Clase.MATERIAS_PRIMAS,
     "region": Region.NA, "sector": Sector.NA, "riesgo": NivelRiesgoActivo.MEDIO, "ter": 0.40},
    {"ticker": "SLV", "nombre": "Plata", "clase": Clase.MATERIAS_PRIMAS,
     "region": Region.NA, "sector": Sector.NA, "riesgo": NivelRiesgoActivo.ALTO, "ter": 0.50},
    {"ticker": "DBC", "nombre": "Materias primas diversificadas", "clase": Clase.MATERIAS_PRIMAS,
     "region": Region.NA, "sector": Sector.NA, "riesgo": NivelRiesgoActivo.ALTO, "ter": 0.85},
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