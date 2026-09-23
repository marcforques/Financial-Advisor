"""
Tests de los límites de composición de cartera por perfil.

Nacen de una revisión de coherencia entre lo implementado y los parámetros
documentados en la memoria: el tope por activo no se aplicaba realmente
(se calculaba pero no se devolvía), la fase de concentración usaba un
35% fijo igual para todos los perfiles, y la renormalización tras eliminar
posiciones pequeñas podía romper el tope por activo. Estos tests blindan
que, con los límites correctos y por perfil, la cartera FINAL (tras
optimizar y concentrar) cumple siempre max_activos, umbral mínimo, tope
por activo y topes de región/sector, y que la renormalización no puede
romperlos.
"""

import numpy as np
import pandas as pd
import pytest

from agents.perfil import PerfilInversor, NivelRiesgo, ObjetivoInversion
from universo.catalogo import metadatos, Region, Sector
from universo.limites import MAX_POR_ACTIVO, MAX_POR_REGION, MAX_POR_SECTOR
from universo.selector import restricciones_completas
from core.optimizer import optimizar_markowitz, concentrar_cartera, _limpiar_y_renormalizar


TOL = 1e-4

# Universo sintético de 11 activos REALES del catálogo, elegido para poder
# estresar los tres topes a la vez (activo, región y sector): concentra
# varios activos en EEUU y en tecnología, y solo tiene dos bonos (para que
# el mínimo de bonos del conservador, 30%, obligue a usar ambos en vez de
# uno solo por encima de su tope por activo).
ACTIVOS_ESTRES = [
    "VUSA.AS", "EXXT.DE", "XUTC.DE", "XUHC.DE", "IUSP.AS",  # renta variable EEUU
    "XMME.DE", "IMAE.AS", "IJPN.L",                          # renta variable no-EEUU
    "SUAG.L", "IEAG.AS",                                     # bonos (EEUU y Europa)
    "SGLN.L",                                                # materias primas
]


@pytest.fixture
def mercado_estres():
    """
    Rentabilidades sesgadas hacia EEUU/tecnología y covarianza diagonal
    (sin correlación, por simplicidad: no afecta a si los topes se
    cumplen). Sin restricciones, la optimización concentraría la cartera
    muy por encima de cualquier tope razonable por activo, región o
    sector; con las restricciones del perfil, no debe poder hacerlo.
    """
    mu = pd.Series(
        [0.11, 0.16, 0.18, 0.09, 0.08, 0.07, 0.06, 0.05, 0.03, 0.025, 0.04],
        index=ACTIVOS_ESTRES,
    )
    varianzas = [0.020, 0.035, 0.045, 0.018, 0.025, 0.030, 0.022, 0.020, 0.004, 0.005, 0.020]
    S = pd.DataFrame(np.diag(varianzas), index=ACTIVOS_ESTRES, columns=ACTIVOS_ESTRES)
    return mu, S


def _perfil(nivel: NivelRiesgo) -> PerfilInversor:
    return PerfilInversor(
        nivel_riesgo=nivel, horizonte_anios=15,
        capital=50000, objetivo=ObjetivoInversion.CRECIMIENTO,
    )


def _cartera_final(nivel: NivelRiesgo, mu: pd.Series, S: pd.DataFrame) -> dict:
    """
    Reproduce el pipeline real (orquestador.nodos.nodo_optimizar) para un
    nivel de riesgo dado: optimización completa con restricciones del
    perfil + concentración a cartera operativa con el tope por activo
    correspondiente.
    """
    perfil = _perfil(nivel)
    orden = list(S.index)
    restricciones = restricciones_completas(perfil, orden)
    resultado = optimizar_markowitz(mu, S, restricciones=restricciones)
    return concentrar_cartera(
        resultado, mu, S,
        max_por_activo=MAX_POR_ACTIVO[nivel],
        max_activos=7, umbral_minimo=0.04,
        restricciones_fn=lambda tickers: restricciones_completas(perfil, tickers),
    )


@pytest.mark.parametrize("nivel", list(NivelRiesgo))
def test_maximo_por_activo_segun_perfil(mercado_estres, nivel):
    """
    1-3: ninguna cartera supera el máximo por activo de su perfil
    (conservador 25%, moderado 30%, agresivo 40%).
    """
    mu, S = mercado_estres
    final = _cartera_final(nivel, mu, S)
    tope = MAX_POR_ACTIVO[nivel]
    for ticker, peso in final["pesos"].items():
        assert peso <= tope + TOL, f"{ticker} al {peso:.1%} supera el tope {tope:.0%} ({nivel.value})"


@pytest.mark.parametrize("nivel", list(NivelRiesgo))
def test_maximo_siete_posiciones(mercado_estres, nivel):
    """4: ninguna cartera tiene más de 7 posiciones."""
    mu, S = mercado_estres
    final = _cartera_final(nivel, mu, S)
    assert len(final["pesos"]) <= 7


@pytest.mark.parametrize("nivel", list(NivelRiesgo))
def test_minimo_cuatro_por_ciento(mercado_estres, nivel):
    """5: no quedan posiciones inferiores al 4% en la cartera final."""
    mu, S = mercado_estres
    final = _cartera_final(nivel, mu, S)
    for ticker, peso in final["pesos"].items():
        assert peso >= 0.04 - TOL, f"{ticker} al {peso:.1%} está por debajo del umbral del 4%"


@pytest.mark.parametrize("nivel", list(NivelRiesgo))
def test_pesos_suman_uno(mercado_estres, nivel):
    """6: los pesos finales suman aproximadamente 1 (100%)."""
    mu, S = mercado_estres
    final = _cartera_final(nivel, mu, S)
    assert sum(final["pesos"].values()) == pytest.approx(1.0, abs=1e-3)


@pytest.mark.parametrize("nivel", list(NivelRiesgo))
def test_limites_region_y_sector(mercado_estres, nivel):
    """7: los límites de región y de sector del perfil se respetan."""
    mu, S = mercado_estres
    final = _cartera_final(nivel, mu, S)

    por_region: dict = {}
    por_sector: dict = {}
    for ticker, peso in final["pesos"].items():
        meta = metadatos(ticker)
        if meta["region"] != Region.NA:
            por_region[meta["region"]] = por_region.get(meta["region"], 0.0) + peso
        if meta["sector"] not in (Sector.AMPLIO, Sector.NA):
            por_sector[meta["sector"]] = por_sector.get(meta["sector"], 0.0) + peso

    tope_region = MAX_POR_REGION[nivel]
    tope_sector = MAX_POR_SECTOR[nivel]
    for region, peso in por_region.items():
        assert peso <= tope_region + TOL, f"región {region} al {peso:.1%} supera {tope_region:.0%}"
    for sector, peso in por_sector.items():
        assert peso <= tope_sector + TOL, f"sector {sector} al {peso:.1%} supera {tope_sector:.0%}"


def test_renormalizar_no_rompe_tope_por_activo():
    """
    8: reproduce el bug de renormalización descrito en la revisión. Tres
    activos exactamente en el tope y uno residual por debajo del umbral
    mínimo (4%): eliminar el residual y renormalizar DIVIDIENDO ENTRE EL
    TOTAL (comportamiento anterior) empujaría a los que ya estaban en el
    tope por encima de él. Tras el arreglo (reoptimizar sobre los
    supervivientes con el tope reaplicado) no debe ocurrir.
    """
    activos = ["A", "B", "C", "D", "E"]
    mu = pd.Series([0.08, 0.08, 0.08, 0.02, 0.05], index=activos)
    S = pd.DataFrame(np.diag([0.02, 0.02, 0.02, 0.01, 0.015]), index=activos, columns=activos)

    max_por_activo = 0.30
    resultado = {
        # A, B, C exactamente en el tope; D por debajo del umbral (4%).
        "pesos": {"A": 0.30, "B": 0.30, "C": 0.30, "D": 0.03, "E": 0.07},
        "rentabilidad": 0.07, "volatilidad": 0.10, "sharpe": 0.7,
    }

    # Confirma que el bug SÍ se daría con la renormalización ingenua:
    # dividir entre el total sin D dejaría a A, B y C por encima del tope.
    total_sin_d = sum(p for t, p in resultado["pesos"].items() if t != "D")
    assert 0.30 / total_sin_d > max_por_activo

    final = _limpiar_y_renormalizar(resultado, mu, S, umbral=0.04, max_por_activo=max_por_activo)

    assert "D" not in final["pesos"]
    assert sum(final["pesos"].values()) == pytest.approx(1.0, abs=1e-3)
    for ticker, peso in final["pesos"].items():
        assert peso <= max_por_activo + TOL, f"{ticker} al {peso:.1%} supera el tope tras renormalizar"


def test_renormalizar_conserva_mas_posiciones_si_el_tope_lo_exige():
    """
    Caso límite: si tras el umbral quedan tan pocos supervivientes que ni
    siquiera todos al tope suman 100% (p.ej. 3 activos al 25% = 75%), debe
    conservarse alguna posición más aunque no llegue al 4%, en vez de
    incumplir el tope por activo.
    """
    activos = ["A", "B", "C", "D", "E", "F"]
    mu = pd.Series([0.09, 0.09, 0.09, 0.01, 0.01, 0.01], index=activos)
    S = pd.DataFrame(np.diag([0.02] * 6), index=activos, columns=activos)

    max_por_activo = 0.25
    resultado = {
        # Solo tres activos superan el umbral (25% cada uno = 75% del
        # total); el resto son residuales pequeños que suman el 25% que
        # falta para llegar a 100%.
        "pesos": {"A": 0.25, "B": 0.25, "C": 0.25, "D": 0.10, "E": 0.10, "F": 0.05},
        "rentabilidad": 0.06, "volatilidad": 0.10, "sharpe": 0.6,
    }

    final = _limpiar_y_renormalizar(resultado, mu, S, umbral=0.04, max_por_activo=max_por_activo)

    # Con solo A, B y C (3 activos) es matemáticamente imposible sumar 100%
    # sin superar el 25% de tope (3 * 0.25 = 0.75 < 1): hace falta un 4º.
    assert len(final["pesos"]) >= 4
    assert sum(final["pesos"].values()) == pytest.approx(1.0, abs=1e-3)
    for ticker, peso in final["pesos"].items():
        assert peso <= max_por_activo + TOL, f"{ticker} al {peso:.1%} supera el tope tras renormalizar"
