"""
Módulo de optimización de carteras.

Responsabilidad: dado un vector de rentabilidades esperadas y una
matriz de covarianzas, calcular los pesos óptimos de la cartera.

Contiene dos enfoques:
  - Markowitz: optimización media-varianza clásica con restricciones.
  - Black-Litterman: ajuste bayesiano de rentabilidades a partir del
    equilibrio de mercado y views (definido más abajo).

El optimizador es agnóstico al origen de `mu`: le da igual si viene de la
media histórica o del posterior de Black-Litterman. Esa independencia es
lo que permite enchufar Black-Litterman sin tocar la optimización.
"""

from typing import Callable

import pandas as pd
from pypfopt import EfficientFrontier, black_litterman
from pypfopt.black_litterman import BlackLittermanModel


def optimizar_markowitz(
    mu: pd.Series,
    S: pd.DataFrame,
    restricciones: list[Callable] | None = None,
    risk_free_rate: float = 0.02
) -> dict:
    """
    Calcula la cartera de máximo Sharpe (Markowitz media-varianza).

    Parameters
    ----------
    mu : pd.Series
        Rentabilidades esperadas anualizadas por activo.
    S : pd.DataFrame
        Matriz de covarianzas anualizada.
    restricciones : list[Callable] | None, opcional
        Lista de funciones lambda que restringen los pesos.
        Ej: [lambda w: w >= 0.05, lambda w: w <= 0.40].
        Si es None, solo se aplican las restricciones por defecto
        (pesos suman 1, sin posiciones cortas).
    risk_free_rate : float, opcional
        Tasa libre de riesgo para el ratio de Sharpe.

    Returns
    -------
    dict
        Con claves "pesos" (dict), "rentabilidad", "volatilidad", "sharpe".
    """
    
    ef = EfficientFrontier(mu, S)
    
    if restricciones:
        for r in restricciones:
            ef.add_constraint(r)
            
    ef.max_sharpe(risk_free_rate=risk_free_rate)
    pesos = ef.clean_weights()
    rent, vol, sharpe = ef.portfolio_performance(risk_free_rate=risk_free_rate)
    
    return {
        "pesos": dict(pesos),
        "rentabilidad": rent,
        "volatilidad": vol,
        "sharpe": sharpe
    }


def rentabilidades_equilibrio(
    market_caps: dict[str, float],
    S: pd.DataFrame,
    delta: float = 2.5
) -> pd.Series:
    """
    Calcula las rentabilidades de equilibrio del mercado (el prior).

    Aplica reverse optimization: deduce qué rentabilidades esperadas
    justifican los pesos de mercado actuales. Es el punto de partida de
    Black-Litterman, más estable que la rentabilidad histórica porque no
    depende de un periodo concreto sino de la estructura de riesgo.

    Fórmula: Pi = delta * S * w_mercado

    Parameters
    ----------
    market_caps : dict[str, float]
        Capitalización (o proxy) de cada activo. Determina los pesos
        de mercado, que se normalizan internamente.
    S : pd.DataFrame
        Matriz de covarianzas anualizada.
    delta : float, opcional
        Aversión al riesgo del mercado. Valor estándar ~2.5.

    Returns
    -------
    pd.Series
        Rentabilidades de equilibrio (prior) por activo.
    """
    return black_litterman.market_implied_prior_returns(market_caps, delta, S)


def optimizar_black_litterman(
    S: pd.DataFrame,
    market_caps: dict[str, float],
    views: dict[str, float],
    restricciones: list[Callable] | None = None,
    delta: float = 2.5,
    risk_free_rate: float = 0.02
    ) -> dict:
    """
    Optimiza una cartera con el modelo Black-Litterman completo.

    Flujo: parte del equilibrio de mercado (prior), incorpora las views
    absolutas con confianza automática para obtener el posterior, y
    optimiza ese posterior con Markowitz (máximo Sharpe) más restricciones.

    Parameters
    ----------
    S : pd.DataFrame
        Matriz de covarianzas anualizada.
    market_caps : dict[str, float]
        Capitalización (o proxy) de cada activo, para el prior.
    views : dict[str, float]
        Views absolutas: rentabilidad esperada por activo según la opinión.
        Ej: {"EEM": 0.12} significa "espero que EEM rente un 12%".
        Solo hace falta incluir los activos sobre los que se opina.
    restricciones : list[Callable] | None, opcional
        Restricciones sobre los pesos (ver optimizar_markowitz).
    delta : float, opcional
        Aversión al riesgo del mercado, para el prior de equilibrio.
    risk_free_rate : float, opcional
        Tasa libre de riesgo para el ratio de Sharpe.

    Returns
    -------
    dict
        Con "pesos", "rentabilidad", "volatilidad", "sharpe" y además
        "posterior" (las rentabilidades ajustadas, para inspección).
    """
    
    # 1. Prior: rentabilidades de equilibrio del mercado.
    prior = rentabilidades_equilibrio(market_caps, S, delta)
    
    # 2. Modelo Black-Litterman: combina prior + vistas -> posterior.
    bl = BlackLittermanModel(
        S,
        pi=prior,
        absolute_views=views,
        omega="default"
    )
    posterior = bl.bl_returns()
    
    # 3. Optimizamos el posterior con nuestro Markowitz ya existente.
    resultado = optimizar_markowitz(
        posterior,
        S,
        restricciones=restricciones,
        risk_free_rate=risk_free_rate
    )
    
    # Añadimos el posterior al resultado para poder inspeccionarlo.
    resultado["posterior"] = dict(posterior)
    return resultado
