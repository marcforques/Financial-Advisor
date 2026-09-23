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

import math
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


def _metricas_cartera(pesos: dict[str, float], mu: pd.Series, S: pd.DataFrame) -> dict:
    """
    Calcula rentabilidad, volatilidad y Sharpe de una cartera ya pesada.
    """
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


def _limitar_pesos(pesos: dict[str, float], max_por_activo: float) -> dict[str, float]:
    """
    Renormaliza a suma 1 sin dejar ningún peso por encima de max_por_activo.

    Si el reparto proporcional supera el tope en algún activo, lo recorta
    al máximo y redistribuye el excedente entre el resto. Itera porque tras
    redistribuir, otro activo puede pasar a superar el tope; converge
    porque cada iteración fija al menos un peso definitivamente.
    """
    fijos: dict[str, float] = {}
    libres = dict(pesos)

    while True:
        excedidos = {t: p for t, p in libres.items() if p > max_por_activo + 1e-9}
        if not excedidos:
            break
        for t in excedidos:
            fijos[t] = max_por_activo
            del libres[t]

        restante = 1.0 - sum(fijos.values())
        suma_libres = sum(libres.values())
        if suma_libres > 0 and restante > 0:
            libres = {t: p / suma_libres * restante for t, p in libres.items()}
        else:
            libres = {t: 0.0 for t in libres}
            break

    return {**fijos, **libres}


def _limpiar_y_renormalizar(
    resultado,
    mu,
    S,
    umbral,
    max_por_activo: float | None = None,
    restricciones_fn: Callable[[list[str]], list[Callable]] | None = None,
):
    """
    Elimina posiciones bajo el umbral y renormaliza a suma 1, sin que eso
    pueda romper el máximo por activo (ni, si se pasa `restricciones_fn`,
    el resto de restricciones del perfil: clase, región, sector).

    Dividir proporcionalmente entre el total tras eliminar posiciones
    pequeñas (el comportamiento anterior) puede empujar un peso que ya
    estaba en el tope por encima de él. En su lugar, reoptimizamos SOLO
    sobre las posiciones supervivientes con las mismas restricciones que
    se aplicaron en la fase anterior.

    Si el tope por activo hace matemáticamente imposible llegar al 100%
    con los supervivientes (p.ej. 3 activos al 25% solo suman 75%), se
    conservan más posiciones aunque no lleguen al umbral: es preferible
    una posición residual pequeña a incumplir el tope por activo.
    """
    pesos_originales = resultado["pesos"]
    ordenados = sorted(pesos_originales.items(), key=lambda x: x[1], reverse=True)
    supervivientes = [t for t, p in ordenados if p >= umbral]

    if max_por_activo:
        minimo_necesario = math.ceil(1.0 / max_por_activo)
        if len(supervivientes) < minimo_necesario:
            supervivientes = [t for t, _ in ordenados[:minimo_necesario]]

    if not supervivientes:
        return {"pesos": {}, "rentabilidad": 0.0, "volatilidad": 0.0, "sharpe": 0.0}

    if set(supervivientes) == set(pesos_originales):
        # No se eliminó ninguna posición: el resultado ya venía de una
        # optimización con restricciones, no hace falta tocar nada.
        final = {
            "pesos": dict(pesos_originales),
            "rentabilidad": resultado["rentabilidad"],
            "volatilidad": resultado["volatilidad"],
            "sharpe": resultado["sharpe"],
        }
    else:
        mu_f = mu[supervivientes]
        S_f = S.loc[supervivientes, supervivientes]

        if restricciones_fn is not None:
            restricciones = restricciones_fn(supervivientes)
        elif max_por_activo is not None:
            restricciones = [lambda w, m=max_por_activo: w <= m]
        else:
            restricciones = None

        try:
            final = optimizar_markowitz(mu_f, S_f, restricciones=restricciones)
        except Exception:
            # Salvaguarda si el solver no converge (caso raro, p.ej.
            # restricciones incompatibles entre sí): renormalizamos
            # proporcionalmente y recortamos manualmente el tope por activo.
            pesos = {t: pesos_originales[t] for t in supervivientes}
            total = sum(pesos.values())
            pesos = {t: p / total for t, p in pesos.items()} if total > 0 else pesos
            final = _metricas_cartera(pesos, mu, S)

    # Defensa en profundidad: pase lo que pase arriba, ningún peso final
    # debe superar el tope por activo.
    if max_por_activo is not None and any(p > max_por_activo + 1e-6 for p in final["pesos"].values()):
        final = _metricas_cartera(_limitar_pesos(final["pesos"], max_por_activo), mu, S)

    return final


def concentrar_cartera(
    resultado,
    mu,
    S,
    max_por_activo: float,
    max_activos: int = 7,
    umbral_minimo: float = 0.04,
    restricciones_fn: Callable[[list[str]], list[Callable]] | None = None,
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
    max_por_activo : float
        Peso máximo por posición. Depende del perfil (no hay un valor
        común válido para todos); lo determina quien conoce el perfil
        (ver universo.limites.MAX_POR_ACTIVO) y se pasa explícitamente.
    max_activos : int
        Número máximo de posiciones.
    umbral_minimo : float
        Peso mínimo por posición; por debajo se elimina.
    restricciones_fn : Callable[[list[str]], list[Callable]], opcional
        Dado un subconjunto de tickers, devuelve TODAS las restricciones
        del perfil (clase, región, sector, activo) para ese subconjunto.
        Si se pasa, se reaplican en cada reoptimización de esta fase para
        que la cartera concentrada final siga respetando región y sector,
        no solo el tope por activo. Si no se pasa, solo se aplica el tope
        por activo.

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
        final = _limpiar_y_renormalizar(
            resultado, mu, S, umbral_minimo, max_por_activo, restricciones_fn
        )
    else:
        # Reoptimizar solo sobre los elegidos, con las restricciones del
        # perfil para ese subconjunto (o, a falta de ellas, solo el tope).
        mu_reducido = mu[tickers_elegidos]
        S_reducido = S.loc[tickers_elegidos, tickers_elegidos]
        if restricciones_fn is not None:
            restr_reducidas = restricciones_fn(tickers_elegidos)
        else:
            restr_reducidas = [lambda w, m=max_por_activo: w <= m]

        resultado_reducido = optimizar_markowitz(mu_reducido, S_reducido, restr_reducidas)
        final = _limpiar_y_renormalizar(
            resultado_reducido, mu_reducido, S_reducido, umbral_minimo,
            max_por_activo, restricciones_fn,
        )

    # Conservar claves extra del resultado original (posterior, etc.).
    for clave in resultado:
        if clave not in final:
            final[clave] = resultado[clave]

    return final