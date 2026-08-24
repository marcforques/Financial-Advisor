"""
Modelos de petición y respuesta de la API.

Definen la forma de los datos que entran y salen por HTTP. Son la
traducción entre el JSON del frontend y los objetos del dominio (como
PerfilInversor). Usar modelos Pydantic da validación automática: si el
frontend envía datos mal formados, FastAPI responde con un error claro.
"""

from pydantic import BaseModel, Field

from agents.perfil import NivelRiesgo, ObjetivoInversion


class PeticionCartera(BaseModel):
    """Datos que el frontend envía para pedir una cartera."""
    nivel_riesgo: NivelRiesgo
    horizonte_anios: int = Field(ge=1, le=50)
    capital: float = Field(gt=0)
    objetivo: ObjetivoInversion
    texto_libre: str = Field(
        default="",
        description="Texto libre del usuario para extraer matices (opcional)."
    )
    usuario_id: str = Field(
        default="usuario_local",
        description="Propietario de la cartera (temporal hasta tener auth)."   
    )
    nombre: str = Field(
        default="",
        decription="Nombre de la cartera; si vacío, se genera uno."
    )


class ActivoCartera(BaseModel):
    """Un activo dentro de la cartera de respuesta."""
    ticker: str
    peso: float
    region: str = ""


class RespuestaCartera(BaseModel):
    """Cartera que la API devuelve al frontend."""
    activos: list[ActivoCartera]
    rentabilidad_esperada: float
    volatilidad: float
    sharpe: float
    explicacion: str
    universo_considerado: int  # cuántos activos se evaluaron
    cartera_id: str | None = None   # id de la cartera guardada automáticamente