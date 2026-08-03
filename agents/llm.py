"""
Cliente LLM centralizado.

Responsabilidad única: crear y configurar el cliente de OpenAI, cargando
la clave de API de forma segura desde el archivo .env.

Todos los agentes obtienen el cliente desde aquí, en lugar de crearlo
cada uno por su cuenta. Centralizar esto significa que si cambias de
proveedor o de configuración, tocas un solo archivo.
"""
import os

from dotenv import load_dotenv
from openai import OpenAI

# Carga las variables del archivo .env al entorno.
load_dotenv(override=True)

# Modelo por defecto. Fijamos una versión concreta para reproducibilidad,
# el mismo modelo se comporta igual entre ejecuciones
MODELO_POR_DEFECTO = "gpt-4o-mini"


def obtener_cliente() -> OpenAI:
    """
    Crea el cliente de OpenAI con la clave del entorno.

    Returns
    -------
    OpenAI
        Cliente configurado y listo para hacer llamadas.

    Raises
    ------
    ValueError
        Si no se encuentra la clave de API en el entorno.
    """
    
    clave = os.getenv("OPENAI_API_KEY")
    
    if not clave:
        raise ValueError(
            "No se encontró OPENAI_API_KEY. Asegúrate de tener un archivo "
            ".env en la raíz del proyecto con tu clave "
        )
    
    return OpenAI(api_key=clave)
