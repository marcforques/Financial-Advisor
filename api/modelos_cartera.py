"""
Modelos de datos de carteras persistentes.

Representan una cartera guardada de un usuario con el detalle necesario
para calcular impuestos reales al rebalancear: cada posición guarda las
participaciones y el precio de compra, no solo el peso.

Los pesos (%) son una VISTA derivada de las participaciones y los precios,
no el dato primario. Esto refleja la realidad: un inversor tiene N
participaciones compradas a un precio, y el peso se calcula a partir de ahí.
"""
from datetime import datetime
from pydantic import BaseModel, Field

from agents.perfil import NivelRiesgo, ObjetivoInversion


class Posicion(BaseModel):
    """
    Una posición concreta en un activo dentro de una cartera.
    """
    ticker: str
    participaciones: float = Field(gt=0, description="Número de participaciones.")
    precio_compra: float = Field(gt=0, description="Precio medio de adquisición.")
    
    def valor(self, precio_actual: float) -> float:
        """
        Valor actual de la posición.
        """
        return self.participaciones * precio_actual

    def ganancia(self, precio_actual: float) -> float:
        """
        Ganancia (o pérdida) latente de la posición.
        """
        return self.participaciones * (precio_actual - self.precio_compra)    
    

class CarteraGuardada(BaseModel):
    """
    Una cartera guardada de un usuario.
    """
    id: str | None = None                # lo asigna la base de datos
    usuario_id: str                       # a quién pertenece
    nombre: str                           # nombre identificativo
    posiciones: list[Posicion]
    nivel_riesgo: NivelRiesgo             # perfil con que se creó
    horizonte_anios: int
    objetivo: ObjetivoInversion
    fecha_creacion: datetime = Field(default_factory=datetime.now)
    es_externa: bool = False              # True si el usuario la introdujo a mano

    def capital_invertido(self) -> float:
        """
        Capital total invertido (a precios de compra).
        """
        return sum(p.participaciones * p.precio_compra for p in self.posiciones)

    def pesos_actuales(self, precios_actuales: dict[str, float]) -> dict[str, float]:
        """
        Calcula los pesos actuales a partir de los valores de mercado.

        Los pesos se DERIVAN del valor actual de cada posición, no se
        guardan. Un activo que subió pesa más ahora que cuando se compró.
        """
        valores = {
            p.ticker: p.valor(precios_actuales.get(p.ticker, p.precio_compra))
            for p in self.posiciones
        }
        total = sum(valores.values())
        if total <= 0:
            return {}
        return {ticker: valor / total for ticker, valor in valores.items()}

    def precios_compra_dict(self) -> dict[str, float]:
        """
        Devuelve {ticker: precio_compra}, para el cálculo de impuestos.
        """
        return {p.ticker: p.precio_compra for p in self.posiciones}