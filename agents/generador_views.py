"""
Agente generador de views para Black-Litterman.

Responsabilidad única: traducir el perfil del inversor y sus matices
cualitativos en views moderadas y justificadas sobre los activos.

DISEÑO CRÍTICO: este agente NO predice el mercado. No responde a "¿qué
activo subirá?". Traduce preferencias del usuario y principios financieros
establecidos en inclinaciones moderadas de cartera, cada una con su
justificación. Esta decisión es lo que hace el sistema defendible: las
views nacen del perfil, no de una adivinación de precios.
"""

from pydantic import BaseModel, Field

from agents.llm import obtener_cliente, MODELO_POR_DEFECTO
from agents.perfil import PerfilInversor


class View(BaseModel):
    """
    Una view individual sobre un activo.
    """
    
    activo: str = Field(description="Ticker del activo (debe estar en el universo).")
    rentabilidad_esperada: float = Field(
        description=(
            "Rentabilidad anual esperada para el activo según la inclinación. "
            "Debe ser una desviación MODERADA respecto a lo normal del activo, "
            "no una apuesta extrema. Rango razonable: 0.02 a 0.12."
        )
    )
    justificacion: str = Field(
        description=(
            "Lista de views moderadas y justificadas. Puede estar vacía si "
            "el perfil no justifica ninguna inclinación particular."
        )
    )
    
class ViewsGeneradas(BaseModel):
    """
    Conjunto de views producidas por el agente.
    """
    
    views: list[View] = Field(
        description=(
            "Lista de views moderadas y justificadas. Puede estar vacía si "
            "el perfil no justifica ninguna inclinación particular."
        )
    )
    
    
    
def generar_views(perfil: PerfilInversor, universo: list[str]) -> ViewsGeneradas:
    """
    Genera views de Black-Litterman a partir del perfil del inversor.

    Parameters
    ----------
    perfil : PerfilInversor
        Perfil completo, incluyendo nivel de riesgo, horizonte y matices.
    universo : list[str]
        Tickers disponibles sobre los que se pueden expresar views.

    Returns
    -------
    ViewsGeneradas
        Views estructuradas, cada una con activo, rentabilidad y justificación.
    """
    
    cliente = obtener_cliente()
    
    contexto = (
        f"Perfil del inversor:\n"
        f"- Nivel de riesgo: {perfil.nivel_riesgo.value}\n"
        f"- Horizonte: {perfil.horizonte_anios} años\n"
        f"- Objetivo: {perfil.objetivo.value}\n"
        f"- Matices personales: {', '.join(perfil.matices) if perfil.matices else 'ninguno'}\n\n"
        f"Universo de activos disponibles: {', '.join(universo)}"
    )
    
    completion = cliente.beta.chat.completions.parse(
        model=MODELO_POR_DEFECTO,
        messages=[
            {
                "role": "system",
                "content": (
                    "Eres un asesor de inversiones que traduce el perfil de un "
                    "cliente en inclinaciones moderadas de cartera (views) para "
                    "el modelo Black-Litterman.\n\n"
                    "REGLAS ESTRICTAS:\n"
                    "1. NUNCA predigas el mercado. No digas que un activo 'subirá'.\n"
                    "2. Cada view debe justificarse por el PERFIL del cliente o "
                    "por principios financieros establecidos (ej: horizonte largo "
                    "tolera más renta variable; oro como cobertura de inflación).\n"
                    "3. Las inclinaciones deben ser MODERADAS, no apuestas extremas.\n"
                    "4. Si el perfil no justifica ninguna inclinación clara, "
                    "devuelve una lista vacía. Es válido no tener views.\n"
                    "5. Solo puedes opinar sobre activos del universo dado."
                )  
            },
            {
                "role": "user",
                "content": contexto
            }
        ],
        response_format=ViewsGeneradas
    )
    
    return completion.choices[0].message.parsed
