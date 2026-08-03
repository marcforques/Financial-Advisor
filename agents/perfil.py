"""
Esquema del perfil de inversor.

Define la estructura de datos que describe a un inversor: su tolerancia
al riesgo, horizonte, capital y objetivos. Es el "contrato" que comparten
el formulario (frontend), el agente de perfilado (LLM) y el optimizador.

Este módulo es código puro sin IA: solo define y valida la forma de los
datos. La extracción desde lenguaje natural vive en el agente.
"""

from enum import Enum
from pydantic import BaseModel, Field

class NivelRiesgo(str, Enum):
    """
    Tolerancia al riesgo del inversor. Determina las restricciones
    que se aplicarán en la optimización de la cartera.
    """
    
    CONSERVADOR = "conservador"
    MODERADO = "moderado"
    AGRESIVO = "agresivo"
    

class ObjetivoInversion(str, Enum):
    """
    Objetivo principal que persigue el inversor
    """
    
    PRESERVAR = "preservar_capital"
    INGRESOS = "generar_ingresos"
    CRECIMIENTO = "crecimiento"
    JUBILACION = "jubilacion"
    

class PerfilInversor(BaseModel):
    """
    Perfil completo de un inversor.

    Reúne toda la información necesaria para construir una cartera
    personalizada. Los campos estructurados vienen del formulario; el
    campo `matices` recoge la interpretación del texto libre por el LLM.
    """
    
    nivel_riesgo: NivelRiesgo = Field(description="Tolerancia al riesgo del inversor.")
    
    horizonte_anios: int = Field(ge=1, le=50, description="Horizonte temporal de la inversión, en años (1-50).")
    
    capital: float = Field(gt=0, description="Capital total a invertir, en euros. Debe ser positivo.")
    
    objetivo: ObjetivoInversion = Field(description="Objetivo principal de la inversión.")
    
    matices: list[str] = Field(default_factory=list, 
                               description=(
                                    "Matices cualitativos extraídos del texto libre por el LLM: "
                                    "preocupaciones, preferencias o circunstacias personales. "
                                    "Vacío si el usuario no aporta texto libre."
                               ))    
    
    