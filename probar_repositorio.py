from persistencia.repositorio import RepositorioSQLite
from api.modelos_cartera import CarteraGuardada, Posicion
from agents.perfil import NivelRiesgo, ObjetivoInversion

# Usamos una base de datos de prueba
repo = RepositorioSQLite("carteras_prueba.db")

# Crear y guardar una cartera
cartera = CarteraGuardada(
    usuario_id="usuario_1",
    nombre="Cartera jubilación",
    posiciones=[
        Posicion(ticker="SPY", participaciones=12, precio_compra=400.0),
        Posicion(ticker="AGG", participaciones=30, precio_compra=100.0),
    ],
    nivel_riesgo=NivelRiesgo.MODERADO,
    horizonte_anios=20,
    objetivo=ObjetivoInversion.JUBILACION,
)

cartera_id = repo.guardar(cartera)
print(f"Cartera guardada con id: {cartera_id}")

# Recuperarla
recuperada = repo.obtener(cartera_id)
print(f"\nRecuperada: {recuperada.nombre}")
print(f"  Posiciones: {[(p.ticker, p.participaciones) for p in recuperada.posiciones]}")
print(f"  Capital invertido: {recuperada.capital_invertido():.2f}€")

# Listar las carteras del usuario
carteras = repo.listar_por_usuario("usuario_1")
print(f"\nCarteras del usuario: {len(carteras)}")

# Guardar una segunda y volver a listar
cartera2 = CarteraGuardada(
    usuario_id="usuario_1", nombre="Cartera externa", es_externa=True,
    posiciones=[Posicion(ticker="QQQ", participaciones=5, precio_compra=350.0)],
    nivel_riesgo=NivelRiesgo.AGRESIVO, horizonte_anios=15,
    objetivo=ObjetivoInversion.CRECIMIENTO,
)
repo.guardar(cartera2)
print(f"Tras guardar otra: {len(repo.listar_por_usuario('usuario_1'))} carteras")