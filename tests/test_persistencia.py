"""
Tests de la capa de persistencia.

Blindan el repositorio de carteras: el ciclo guardar-recuperar-listar-
eliminar, y que los datos delicados (precios de compra, pesos objetivo)
sobreviven intactos al viaje a la base de datos. Nacen en parte de un bug
real: el pesos_objetivo no se guardaba porque faltaba en la tabla SQLite.

Cada test usa una base de datos temporal aislada.
"""

import os
import tempfile

import pytest

from persistencia.repositorio import RepositorioSQLite
from api.modelos_cartera import CarteraGuardada, Posicion
from agents.perfil import NivelRiesgo, ObjetivoInversion


@pytest.fixture
def repo():
    """
    Repositorio con una base de datos temporal, borrada al terminar.

    En Windows, SQLite puede mantener el archivo bloqueado; ignoramos el
    error de borrado si ocurre (el archivo temporal se limpia solo al final).
    """
    fd, ruta = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    repositorio = RepositorioSQLite(ruta)
    yield repositorio
    # Intentar borrar; en Windows puede estar bloqueado, no es crítico.
    try:
        os.remove(ruta)
    except (PermissionError, OSError):
        pass  # el temp se limpiará al reiniciar; no rompemos el test por esto
    
def _cartera_ejemplo(usuario="u1", externa=False, con_objetivo=True):
    return CarteraGuardada(
        usuario_id=usuario,
        nombre="Cartera test",
        posiciones=[
            Posicion(ticker="SPY", participaciones=10, precio_compra=400.0),
            Posicion(ticker="AGG", participaciones=20, precio_compra=100.0),
        ],
        nivel_riesgo=NivelRiesgo.MODERADO,
        horizonte_anios=15,
        objetivo=ObjetivoInversion.JUBILACION,
        es_externa=externa,
        pesos_objetivo={"SPY": 0.5, "AGG": 0.5} if con_objetivo else None
    )
    
def test_guardar_asigna_id(repo):
    """
    Guardar una cartera sin id le asigna uno.
    """
    cartera = _cartera_ejemplo()
    assert cartera.id is None
    cartera_id = repo.guardar(cartera)
    assert cartera_id is not None
    

def test_guardar_y_recuperar(repo):
    """
    Una cartera recuperada es igual a la guardada.
    """
    cartera_id = repo.guardar(_cartera_ejemplo())
    recuperada = repo.obtener(cartera_id)

    assert recuperada is not None
    assert recuperada.nombre == "Cartera test"
    assert len(recuperada.posiciones) == 2


def test_precios_compra_sobreviven(repo):
    """
    Los precios de compra deben conservarse intactos (clave para impuestos).
    """
    cartera_id = repo.guardar(_cartera_ejemplo())
    recuperada = repo.obtener(cartera_id)

    precios = recuperada.precios_compra_dict()
    assert precios["SPY"] == 400.0
    assert precios["AGG"] == 100.0


def test_pesos_objetivo_sobreviven(repo):
    """
    El pesos_objetivo debe persistir (bug real que arreglamos).
    """
    cartera_id = repo.guardar(_cartera_ejemplo(con_objetivo=True))
    recuperada = repo.obtener(cartera_id)

    assert recuperada.pesos_objetivo is not None
    assert recuperada.pesos_objetivo["SPY"] == 0.5
    

def test_cartera_externa_sin_objetivo(repo):
    """
    Una cartera externa puede guardarse con pesos_objetivo None.
    """
    cartera_id = repo.guardar(_cartera_ejemplo(externa=True, con_objetivo=False))
    recuperada = repo.obtener(cartera_id)

    assert recuperada.es_externa is True
    assert recuperada.pesos_objetivo is None


def test_listar_por_usuario(repo):
    """
    Listar devuelve solo las carteras del usuario indicado.
    """
    repo.guardar(_cartera_ejemplo(usuario="ana"))
    repo.guardar(_cartera_ejemplo(usuario="ana"))
    repo.guardar(_cartera_ejemplo(usuario="beto"))

    de_ana = repo.listar_por_usuario("ana")
    de_beto = repo.listar_por_usuario("beto")

    assert len(de_ana) == 2
    assert len(de_beto) == 1


def test_obtener_inexistente_devuelve_none(repo):
    """
    Obtener una cartera que no existe devuelve None.
    """
    assert repo.obtener("id-que-no-existe") is None


def test_eliminar(repo):
    """
    Eliminar una cartera la quita del repositorio.
    """
    cartera_id = repo.guardar(_cartera_ejemplo())
    assert repo.eliminar(cartera_id) is True
    assert repo.obtener(cartera_id) is None
    

def test_eliminar_inexistente(repo):
    """
    Eliminar algo que no existe devuelve False.
    """
    assert repo.eliminar("id-que-no-existe") is False