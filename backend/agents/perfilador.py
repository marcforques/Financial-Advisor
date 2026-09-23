"""
Agente de perfilado.

Responsabilidad única: interpretar el texto libre que escribe el usuario
sobre sus objetivos y preocupaciones, y extraer de él matices cualitativos
estructurados.
"""

from pydantic import BaseModel, Field

from agents.llm import obtener_cliente, MODELO_POR_DEFECTO


class MaticesExtraidos(BaseModel):
    """
    Matices cualitativos extraídos del texto libre del usuario.
    """
    
    matices: list[str] = Field(
        description=(
            "Lista de preocupaciones, preferencias o circunstancias "
            "personales relevantes para la inversión, extraídas del texto. "
            "Cada matiz es una frase corta y concreta. Si el texto no "
            "aporta nada relevante, lista vacía."
        )
    )
    
    resumen: str = Field(
        description=(
            "Resumen en una frase de la actitud inversora que refleja "
            "el texto. Vacío si no hay información suficiente."
        )
    )
    

def extraer_matices(texto_libre: str) -> MaticesExtraidos:
    """
    Extrae matices cualitativos del texto libre del usuario.
    """
    
    # Si no hay texto, no gastamos una llamada al LLM
    if not texto_libre or not texto_libre.strip():
        return MaticesExtraidos(matices=[], resumen="")
    
    cliente = obtener_cliente()
    
    completion = cliente.beta.chat.completions.parse(
        model=MODELO_POR_DEFECTO,
        messages=[
            {
                "role": "system",
                "content": (
                    "Eres un asistente experto en perfilado de inversores. "
                    "Tu tarea es extraer matices cualitativos del texto que "
                    "escribe un usuario sobre su situación financiera. "
                    "Identifica preocupaciones (miedo a perder dinero, "
                    "necesidad de liquidez), preferencias (inversión ética, "
                    "sectores concretos) y circunstancias (jubilación cercana, "
                    "hijos, herencia). No inventes información que no esté "
                    "en el texto. No des consejos de inversión."
                )
            },
            {
                "role": "user",
                "content": texto_libre
            }
        ], 
        response_format=MaticesExtraidos
    )
    
    return completion.choices[0].message.parsed