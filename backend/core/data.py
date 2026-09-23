"""
Módulo de datos de mercado.

Responsabilidad: obtener precios históricos ajustados de forma
reproducible, cacheándolos en disco para no depender de descargas repetidas.
"""

import hashlib
from pathlib import Path

import pandas as pd
import yfinance as yf

# Carpeta donde se cachean los precios. Relativa a la raíz del proyecto.
_CACHE_DIR = Path("data")


def descargar_precios (
    tickers: list[str],
    inicio: str,
    fin: str,
    usar_cache: bool = True
    ) -> pd.DataFrame:
    
    """
    Descarga precios de cierre ajusatados y los cachea en Parquet.
    
    Los precios se descargan una sola vez por combincaciçon de parámetros y
    se guardan en disco. Llamadas posteriores con los mismos parámetros 
    leen del caché, garantizando reproducibilidad: los mismos tickers y
    fechas devuelven siempre exactamente los mismos datos.
    """
    
    _CACHE_DIR.mkdir(exist_ok=True)

    # Nombre de caché único por combinación de tickers y fechas.
    #
    # No se usan los tickers tal cual en el nombre del archivo: con
    # universos grandes (p.ej. el perfil agresivo, que ve casi todo el
    # catálogo) y los tickers UCITS actuales, más largos que los
    # US-listed originales (llevan sufijo de bolsa: .AS, .DE, .L),
    # concatenar todos los tickers podía superar el límite de longitud de
    # ruta de Windows (MAX_PATH, 260 caracteres) y la descarga fallaba con
    # OSError: [Errno 22] Invalid argument. Se usa en su lugar un hash
    # corto de la combinación exacta de tickers y fechas: sigue siendo
    # determinista (mismos tickers + mismas fechas -> mismo archivo,
    # reutilizable de una ejecución a otra) y el nombre nunca crece con el
    # tamaño del universo.
    firma = "_".join(sorted(tickers)) + f"_{inicio}_{fin}"
    hash_firma = hashlib.sha256(firma.encode()).hexdigest()[:16]
    clave = f"precios_{len(tickers)}activos_{inicio}_{fin}_{hash_firma}.parquet"
    ruta_cache = _CACHE_DIR / clave
    
    if usar_cache and ruta_cache.exists():
        return pd.read_parquet(ruta_cache)
    
    datos = yf.download(
        tickers,
        start=inicio,
        end=fin,
        auto_adjust=True,
        progress=False
    )    
    
    if datos.empty:
        raise ValueError(
            f"La descarga no devolvía datos para {tickers} "
            f"entre {inicio} y {fin}."
        )
    
    # Con varios tickers, yfinance devuelve columnas multinivel.
    # Nos quedamos con el precio de cierre (ya ajustado).
    precios = datos["Close"]
    
    # Si es un solo ticker, "Close" devuelve una Series: la volvemos DataFrame.
    if isinstance(precios, pd.Series):
        precios = precios.to_frame()
        
    precios.to_parquet(ruta_cache)
    return precios


def calcular_rentabilidades(
    precios: pd.DataFrame,
    tipo: str = "simple"
) -> pd.DataFrame:
    """
    Calcula las rentabilidades diarias a partir de los precios.
    """
    if tipo == "simple":
        rentabilidades = precios.pct_change()
    elif tipo == "log":
        import numpy as np
        
        rentabilidades = np.log(precios / precios.shift(1))
    else:
        raise ValueError(
            f"tipo debe ser 'simple' o 'log', se recibió '{tipo}'."
        )
        
    return rentabilidades.dropna()


def obtener_precios_actuales(tickers: list[str]) -> dict[str, float]:
    """
    Obtiene la última cotización disponible de cada ticker (sin caché:
    por definición un precio "actual" no debe reutilizarse al día siguiente).
    """
    precios = {}
    for ticker in tickers:
        info = yf.Ticker(ticker).fast_info
        precios[ticker] = float(info["last_price"])
    return precios