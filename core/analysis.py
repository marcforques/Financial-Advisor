"""
Módulo de análisis cuantitativo.

Responsabilidad: transformar precios en los ingredientes estadísticos
que consume el optimizador (rentabilidades esperadas y matriz de covarianzas)
y calcular las métricas de riesgo/rentabilidad de una cartera.

Aquí NO se optimiza nada: solo se preparan y miden magnitudes. La
optimización vive en optimizer.py.
"""

import pandas as pd
import numpy as np
from pypfopt import expected_returns, risk_models


# Días hábiles de mercado al año. Constante estándar en finanzas.
DIAS_MERCADO = 252


def rentabilidades_esperadas(precios: pd.DataFrame) -> pd.Series:
    """
    Calcula la rentabilidad esperada anualizada de cada activo.

    Usa la media histórica de las rentabilidades como estimación del
    retorno futuro esperado. Es el vector `mu` que consume el optimizador.

    Parameters
    ----------
    precios : pd.DataFrame
        Precios ajustados. Índice = fechas, columnas = tickers.

    Returns
    -------
    pd.Series
        Rentabilidad esperada anualizada por activo.
    """
    return expected_returns.mean_historical_return(precios)


def matriz_covarianzas(precios: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula la matriz de covarianzas anualizada.

    Es la matriz `S` (Sigma) que captura la volatilidad de cada activo y
    cómo se relacionan entre sí. Ingrediente esencial de la optimización.

    Parameters
    ----------
    precios : pd.DataFrame
        Precios ajustados.

    Returns
    -------
    pd.DataFrame
        Matriz de covarianzas anualizada (n_activos x n_activos).
    """
    return risk_models.sample_cov(precios)


def metricas_cartera(
    pesos: dict[str, float],
    mu: pd.Series,
    S: pd.DataFrame,
    risk_free_ratio: float = 0.02
) -> dict[str, float]:
    """
    Calcula rentabilidad, volatilidad y ratio de Sharpe de una cartera.

    Parameters
    ----------
    pesos : dict[str, float]
        Peso de cada activo (deben sumar aproximadamente 1).
    mu : pd.Series
        Rentabilidades esperadas anualizadas.
    S : pd.DataFrame
        Matriz de covarianzas anualizada.
    risk_free_rate : float, opcional
        Tasa libre de riesgo para el cálculo del Sharpe.

    Returns
    -------
    dict[str, float]
        Diccionario con "rentabilidad", "volatilidad" y "sharpe".
    """
    
    # Ordenamos los pesos según el orden de los actibos en mu.
    w = np.array([pesos[activo] for activo in mu.index])
    
    rentabilidad = float(w @ mu)
    volatilidad = float(np.sqrt(w @ S.values @ w))
    sharpe = (rentabilidad -risk_free_ratio) / volatilidad
    
    return {
        "rentabilidad": rentabilidad,
        "volatilidad": volatilidad,
        "sharpe": sharpe
    }