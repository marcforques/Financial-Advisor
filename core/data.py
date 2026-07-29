"""
Módulo de datos de mercado.

Responsabilidad: obtener precios históricos ajustados de forma
reproducible, cacheándolos en disco para no depender de descargas repetidas.

El resto del sistema NUNCA descarga datos directamente, siempre pasa por
aquí. Esto centraliza la reproducibilidad en un solo punto.
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
    
    Parameters
    ----------
    tickers : list[str]
        Símbolos de los activos a descargar.
    inicio : str
        Fecha de inicio en formato "YYYY-MM-DD".
    fin : str
        Fecha de fin de formato "YYYY-MM-DD". Deber ser fija, nunca "hoy",
        para no romper la reproducibilidad.
    usar_cache : bool, opcional
        Si True (por defecto), usa el caché si existe. Si False, fuerza
        una descarga nueva y sobreescribe el caché.
        
    
    Returns
    -------
    pd.DatFrame
        Precios de cierre ajustados. índice = fechas, columnas = tickers.
        
    
    Raises
    ------
    ValueError
        Si la descarga no devuelve datos para ningún ticker.
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
    
    Parameters
    ----------
    precios: pd.DataFrame
        Precios ajustados (salida de `descargar_precios`).
    tipo: str, opcional
        "simple" para rentabilidades aritméticas (P1-P0)/P0, usadas en
        optimización de carteras. "log" para logarítmicas ln(P1/P0),
        usadas en análisis estadístico de series temporales.

    Returns
    -------
    pd.DataFrame
        Rentabilidades diarias, sin la primera fila (que sería NaN).

    Raises
    ------
    ValueError
        Si `tipo` no es "simple" ni "log".
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