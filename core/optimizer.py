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
import numpy as np

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


def optimizar_concentrada(
    mu,
    S,
    restricciones=None,
    max_activos: int = 7,
    umbral_minimo: float = 0.04,
    max_por_activo: float = 0.35,
):
    """Optimiza y reduce a una cartera concentrada y operativa.

    Proceso en dos fases:
      1. Optimiza sobre todo el universo.
      2. Selecciona los `max_activos` con más peso.
      3. Reoptimiza SOLO sobre esos, con un tope por activo para que
         ninguno domine (evita concentración excesiva tras reducir).
      4. Aplica el umbral mínimo y renormaliza.

    Parameters
    ----------
    (igual que antes)
    max_por_activo : float
        Peso máximo de cualquier posición en la reoptimización.

    Returns
    -------
    dict
        Cartera final {ticker: peso}, con métricas.
    """
    # --- Fase 1: optimización completa sobre todo el universo ---
    resultado_completo = optimizar_markowitz(mu, S, restricciones)
    pesos_completos = resultado_completo["pesos"]

    # --- Fase 2: seleccionar los max_activos con más peso ---
    mejores = sorted(
        pesos_completos.items(), key=lambda x: x[1], reverse=True
    )[:max_activos]
    tickers_elegidos = [t for t, _ in mejores]

    # Atajo: solo si ya hay pocos activos Y ninguno excede el tope por activo.
    # Si algún activo supera max_por_activo, forzamos la fase 3 para corregirlo.
    activos_sobre_umbral = [p for p in pesos_completos.values() if p > umbral_minimo]
    algun_exceso = any(p > max_por_activo for p in pesos_completos.values())
    if len(activos_sobre_umbral) <= max_activos and not algun_exceso:
        return _limpiar_y_renormalizar(resultado_completo, mu, S, umbral_minimo)

    # --- Fase 3: reoptimizar solo sobre los elegidos, con tope por activo ---
    mu_reducido = mu[tickers_elegidos]
    S_reducido = S.loc[tickers_elegidos, tickers_elegidos]

    # Tope por activo: ninguna posición domina la cartera concentrada.
    orden = list(S_reducido.index)
    restr_tope = [lambda w, m=max_por_activo: w <= m]

    resultado_reducido = optimizar_markowitz(mu_reducido, S_reducido, restr_tope)

    # --- Fase 4: limpiar umbral y renormalizar ---
    return _limpiar_y_renormalizar(resultado_reducido, mu_reducido, S_reducido, umbral_minimo)



def _limpiar_y_renormalizar(resultado, mu, S, umbral):
    """
    Elimina posiciones bajo el umbral y renormaliza a suma 1.
    """
    pesos = {t: p for t, p in resultado["pesos"].items() if p >= umbral}
    total = sum(pesos.values())
    if total > 0:
        pesos = {t: p / total for t, p in pesos.items()}

    # Recalcular métricas con los pesos finales.
    tickers = list(pesos.keys())
    w = np.array([pesos[t] for t in tickers])
    mu_f = mu[tickers].values
    S_f = S.loc[tickers, tickers].values

    rent = float(w @ mu_f)
    vol = float(np.sqrt(w @ S_f @ w))
    sharpe = rent / vol if vol > 0 else 0.0

    return {
        "pesos": pesos,
        "rentabilidad": rent,
        "volatilidad": vol,
        "sharpe": sharpe
    }
    
    
def concentrar_cartera(
    resultado,
    mu,
    S,
    max_activos: int = 7,
    umbral_minimo: float = 0.04,
    max_por_activo: float = 0.35,
):
    """Reduce una cartera ya optimizada a pocas posiciones operativas.

    Toma el resultado de una optimización (Markowitz o Black-Litterman) y
    lo concentra: se queda con los mejores activos y reoptimiza entre ellos
    con un tope por activo, evitando residuales y concentración excesiva.

    Funciona igual para ambos optimizadores porque solo necesita los pesos
    del resultado, las rentabilidades usadas (mu) y la covarianza (S).

    Parameters
    ----------
    resultado : dict
        Resultado de una optimización, con clave "pesos".
    mu : pd.Series
        Rentabilidades usadas en la optimización (prior o posterior de BL).
    S : pd.DataFrame
        Matriz de covarianzas.
    max_activos : int
        Número máximo de posiciones.
    umbral_minimo : float
        Peso mínimo por posición; por debajo se elimina.
    max_por_activo : float
        Peso máximo por posición en la reoptimización.

    Returns
    -------
    dict
        Cartera concentrada {pesos, rentabilidad, volatilidad, sharpe},
        conservando las claves extra del resultado original (posterior, etc.).
    """
    pesos_completos = resultado["pesos"]

    # Seleccionar los max_activos con más peso.
    mejores = sorted(
        pesos_completos.items(), key=lambda x: x[1], reverse=True
    )[:max_activos]
    tickers_elegidos = [t for t, _ in mejores]

    # Atajo: si ya hay pocos activos Y ninguno excede el tope, solo limpiar.
    activos_sobre_umbral = [p for p in pesos_completos.values() if p > umbral_minimo]
    algun_exceso = any(p > max_por_activo for p in pesos_completos.values())
    if len(activos_sobre_umbral) <= max_activos and not algun_exceso:
        final = _limpiar_y_renormalizar(resultado, mu, S, umbral_minimo)
    else:
        # Reoptimizar solo sobre los elegidos, con tope por activo.
        mu_reducido = mu[tickers_elegidos]
        S_reducido = S.loc[tickers_elegidos, tickers_elegidos]
        restr_tope = [lambda w, m=max_por_activo: w <= m]
        resultado_reducido = optimizar_markowitz(mu_reducido, S_reducido, restr_tope)
        final = _limpiar_y_renormalizar(resultado_reducido, mu_reducido, S_reducido, umbral_minimo)

    # Conservar claves extra del resultado original (posterior, etc.).
    for clave in resultado:
        if clave not in final:
            final[clave] = resultado[clave]

    return final