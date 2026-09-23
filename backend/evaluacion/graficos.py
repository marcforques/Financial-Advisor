"""
Gráficos de evaluación.

Genera visualizaciones del rendimiento de las carteras para el capítulo
de resultados: evolución del valor en el tiempo y comparación de perfiles.

Los gráficos se guardan en la carpeta 'figuras/' para incluirlos en la
memoria.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from core.analysis import rentabilidades_esperadas, matriz_covarianzas
from core.optimizer import optimizar_markowitz
from evaluacion.backtest import rendimiento_backtest


# Carpeta de salida para las figuras.
_FIGURAS = Path("figuras")

# Paleta de colores consistente y profesional.
_COLORES = ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B3"]


def _preparar_figura():
    """
    Configuración estética común para todas las figuras.
    """
    _FIGURAS.mkdir(exist_ok=True)
    plt.figure(figsize=(10, 6))
    plt.grid(True, alpha=0.3, linestyle="--")
    

def grafico_evolucion_carteras(
    carteras: dict[str, dict],
    precios_test: pd.DataFrame,
    titulo: str = "Evolución del valor de las carteras (2020-2025)",
    nombre_archivo: str = "evolucion_carteras.png"
) -> str:
    """
    Dibuja la evolución del valor de varias carteras en el periodo test.
    """
    _preparar_figura()
    
    for i, (nombre, pesos) in enumerate(carteras.items()):
        metricas = rendimiento_backtest(pesos, precios_test)
        serie = metricas["serie_valor"]
        color = _COLORES[i % len(_COLORES)]
        plt.plot(serie.index, serie.values, label=nombre, color=color, linewidth=1.8)
    
    plt.title(titulo, fontsize=13, fontweight="bold")
    plt.xlabel("Fecha")
    plt.ylabel("Valor (inicio = 1€)")
    plt.legend(loc="upper left", framealpha=0.9)
    plt.axhline(y=1.0, color="gray", linestyle=":", alpha=0.5)
    plt.tight_layout()
    
    ruta = _FIGURAS / nombre_archivo
    plt.savefig(ruta, dpi=150, bbox_inches="tight")
    plt.close()
    
    return str(ruta)


def grafico_comparacion_perfiles(
    carteras_por_perfil: dict[str, dict],
    precios_test: pd.DataFrame,
    nombre_archivo: str = "comparacion_perfiles.png"
) -> str:
    """
    Compara la evolución de las carteras de distintos perfiles de riesgo.
    """
    _preparar_figura()
    
    # Colores que refuerzan la narrativa: verde=seguro, rojo=arriesgado.
    colores_perfil = {
        "Conservador": "#55A868",
        "Moderado": "#4C72B0",
        "Agresivo": "#C44E52"
    }
    
    for nombre, pesos in carteras_por_perfil.items():
        metricas = rendimiento_backtest(pesos, precios_test)
        serie = metricas["serie_valor"]
        color = colores_perfil.get(nombre, "#8172B3")
        dd = metricas["max_drawdown"] * 100
        etiqueta = f"{nombre} (DD: {dd:.1f}%)"
        plt.plot(serie.index, serie.values, label=etiqueta, color=color, linewidth=1.8)
        
    plt.title(
        "Comparación de perfiles de riesgo (2020-2025)",
        fontsize=13, fontweight="bold"
    )
    plt.xlabel("Fecha")
    plt.ylabel("Valor (inicio = 1€)")
    plt.legend(loc="upper left", framealpha=0.9)
    plt.axhline(y=1.0, color="gray", linestyle=":", alpha=0.5)
    plt.tight_layout()
    
    ruta = _FIGURAS / nombre_archivo
    plt.savefig(ruta, dpi=150, bbox_inches="tight")
    plt.close()
    
    return str(ruta)
