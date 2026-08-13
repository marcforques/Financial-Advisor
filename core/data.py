"""
Módulo de datos de mercado.

Responsabilidad: obtener precios históricos ajustados de forma
reproducible, cacheándolos en disco para no depender de descargas repetidas.
"""

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
    
    # Nombre de caché único por combincación de tickers y fechas.
    clave = f"{'_'.join(sorted(tickers))}_{inicio}_{fin}.parquet"
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