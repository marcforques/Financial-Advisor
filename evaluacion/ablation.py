"""
Estudio de ablación: ¿qué aporta cada componente del sistema?

Compara varias configuraciones sobre el mismo backtest con separación
temporal. Quitando o añadiendo piezas (restricciones, Black-Litterman) y
midiendo el resultado en datos no vistos, se demuestra con evidencia
—no por suposición— qué aporta cada componente.

Todas las configuraciones optimizan con los MISMOS datos de entrenamiento
y se evalúan en el MISMO periodo de prueba, para que la comparación sea
justa.
"""

import numpy as np
import pandas as pd

from core.analysis import rentabilidades_esperadas, matriz_covarianzas
from core.optimizer import optimizar_black_litterman, optimizar_markowitz
from evaluacion.backtest import rendimiento_backtest


def _cartera_equiponderada(activos: list[str]) -> dict[str, float]:
    """
    Cartera ingenua: mismo peso a cada activo. La referencia 'tonta'.
    """
    peso = 1.0 / len(activos)
    return {a: peso for a in activos}


def ejecutar_ablation(
    precios_train: pd.DataFrame,
    precios_test: pd.DataFrame,
    market_caps: dict[str, float],
    restricciones_perfil: list = None,
    views: dict[str, float] = None 
) -> pd.DataFrame:
    """
    Ejecuta el estudio de ablación y devuelve una tabla comparativa.

    Parameters
    ----------
    precios_train : pd.DataFrame
        Precios del periodo de entrenamiento (para optimizar).
    precios_test : pd.DataFrame
        Precios del periodo de prueba (para medir, datos no vistos).
    market_caps : dict[str, float]
        Capitalizaciones para Black-Litterman.
    restricciones_perfil : list, opcional
        Restricciones de perfil a aplicar en la configuración con perfil.
    views : dict[str, float], opcional
        Views para la configuración de Black-Litterman.

    Returns
    -------
    pd.DataFrame
        Tabla con una fila por configuración y las métricas de cada una.
    """
    activos = list(precios_train.columns)
    mu = rentabilidades_esperadas(precios_train)
    S = matriz_covarianzas(precios_train)
    
    configuraciones ={}
    
    # 1. Equiponderada (referencia ingenua).
    configuraciones["1. Equiponderada"] = _cartera_equiponderada(activos)
    
    # 2. Markowitz sin restricciones.
    r2 = optimizar_markowitz(mu, S)
    configuraciones["2. Markowitz puro"] = r2["pesos"]
    
    # 3. Markowitz con restricciones de perfil.
    if restricciones_perfil:
        r3 = optimizar_markowitz(mu, S, restricciones=restricciones_perfil)
        configuraciones["3. Markowitz + perfil"] = r3["pesos"]
        
    # 4. Black-Litterman (con views y restricciones).
    if views:
        r4 = optimizar_black_litterman(
            S, market_caps, views, restricciones=restricciones_perfil
        )
        configuraciones["4. Balck-Litterman"] = r4["pesos"]
    
    # Evaluar cada configuración con el MISMO perido de prueba.
    filas = []
    for nombre, pesos in configuraciones.items():
        metricas = rendimiento_backtest(pesos, precios_test)
        filas.append({
            "Configuración": nombre,
            "Rent. anual": f"{metricas['rentabilidad']*100:.1f}%",
            "Volatilidad": f"{metricas['volatilidad']*100:.1f}%",
            "Sharpe": f"{metricas['sharpe']:.2f}",
            "Max DD": f"{metricas['max_drawdown']*100:.1f}%",
            "Valor final": f"{metricas['valor_final']:.2f}"
        })
    
    return pd.DataFrame(filas)

