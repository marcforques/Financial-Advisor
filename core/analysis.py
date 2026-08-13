"""
Módulo de análisis cuantitativo.

Responsabilidad: transformar precios en los ingredientes estadísticos
que consume el optimizador (rentabilidades esperadas y matriz de covarianzas)
y calcular las métricas de riesgo/rentabilidad de una cartera.
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
    """
    return expected_returns.mean_historical_return(precios)


def matriz_covarianzas(precios: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula la matriz de covarianzas anualizada.

    Es la matriz `S` (Sigma) que captura la volatilidad de cada activo y
    cómo se relacionan entre sí. Ingrediente esencial de la optimización.
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