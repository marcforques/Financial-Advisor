"""
Backtesting de carteras con separación temporal.

Evalúa cómo habría rendido una cartera en un periodo de PRUEBA usando
pesos calculados en un periodo de ENTRENAMIENTO anterior. La separación
temporal evita el look-ahead bias: la cartera se enfrenta a datos que no
vio al optimizarse.
"""
import numpy as np
import pandas as pd

DIAS_MERCADO = 252

def rendimiento_backtest(
    pesos: dict[str, float], 
    precios_prueba: pd.DataFrame, 
    risk_free_rate: float = 0.02) -> dict:
    """
    Calcula el rendimiento real de una cartera en el periodo de prueba.
    """
    # Rentabilidades diarias del periodo de prueba.
    rent_diarias = precios_prueba.pct_change().dropna()
    
    # Alineamos los pesos con las columnas disponibles.
    activos = [a for a in pesos if a in rent_diarias.columns]
    w = np.array([pesos[a] for a in activos])
    w = w / w.sum()     # renormalizar por si falta algún activo
    
    # Rentabilidad diaria de la cartera = suma ponderada.
    rent_cartera = (rent_diarias[activos] * w).sum(axis=1)
    
    # Valor acumulado de la cartera (empezando en 1).
    valor = (1 + rent_cartera).cumprod()
    
    # Métricas anualizadas.
    rent_anual = rent_cartera.mean() * DIAS_MERCADO
    vol_anual = rent_cartera.std() * np.sqrt(DIAS_MERCADO)
    sharpe = (rent_anual - risk_free_rate) / vol_anual if vol_anual > 0 else 0.0
    
    # Máximo drawdown: la peor caída desde un máximo previo.
    maximo_previo = valor.cummax()
    drawdown = (valor - maximo_previo) / maximo_previo
    max_drawdown = drawdown.min()
    
    return {
        "rentabilidad" : float(rent_anual),
        "volatilidad": float(vol_anual),
        "sharpe": float(sharpe),
        "max_drawdown": float(max_drawdown),
        "valor_final": float(valor.iloc[-1]),
        "serie_valor": valor
    }
    


    