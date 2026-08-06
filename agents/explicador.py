"""
Agente explicador.

Responsabilidad única: traducir una cartera ya calculada (con sus pesos,
métricas y justificaciones) en una explicación clara y honesta para el
usuario, apoyándose en el RAG para los conceptos financieros.

REGLA DE ORO: el explicador NO decide ni modifica la cartera. La cartera
llega ya calculada por el código determinista. El LLM solo comunica: coge
datos y justificaciones existentes y los expresa en lenguaje natural,
anclando los conceptos en la base de conocimiento para no alucinar.
"""

from agents.llm import obtener_cliente, MODELO_POR_DEFECTO
from agents.perfil import PerfilInversor
from rag.base_conocimiento import BaseConocimiento


def _recuperar_contexto(kb: BaseConocimiento, resultado: dict) -> str:
    """
    Recupera del RAG los conceptos relevantes para esta cartera.

    Hace consultas dirigidas (específicas) sobre los conceptos que
    aparecen en la explicación, aprovechando que el RAG funciona mejor
    con consultas concretas que con preguntas vagas.
    """
    # Consultas específicas sobre los conceptos que se van a explicar.
    conceptos = [
        "qué es la diversificación de una cartera",
        "qué mide el ratio de Sharpe",
        "qué es la volatilidad de la inversión"
    ]
    
    fragmentos = []
    for concepto in conceptos:
        docs = kb.buscar(concepto, n_resultados=1)
        if docs:
            fragmentos.append(docs[0])
            
    return "\n\n".join(fragmentos)


def explicar_cartera(
    perfil: PerfilInversor,
    resultado: dict,
    kb: BaseConocimiento
    ) -> str:
    """
    Genera una explicación en lenguaje natural de la cartera recomendada.

    Parameters
    ----------
    perfil : PerfilInversor
        Perfil del inversor.
    resultado : dict
        Salida del pipeline: pesos, métricas, views usadas.
    kb : BaseConocimiento
        Base de conocimiento para anclar los conceptos.

    Returns
    -------
    str
        Explicación clara y honesta de la cartera.
    """
    cliente = obtener_cliente()
    
    # Recuperar conocimiento fiable del RAG.
    contexto_rag = _recuperar_contexto(kb, resultado)
    
    # Preparar los datos de la cartera de forma legible.
    pesos_texto = "\n".join(
        f"- {activo}: {peso*100:.1f}%"
        for activo, peso in resultado["pesos"].items()
        if peso > 0.001
    )
    
    justificaciones = "\n".join(
        f"- {v['activo']}: {v['justificacion']}"
        for v in resultado.get("views_usadas", [])
    )
    
    datos = (
        f"PERFIL DEL INVERSOR:\n"
        f"- Riesgo: {perfil.nivel_riesgo.value}\n"
        f"- Horizonte: {perfil.horizonte_anios} años \n"
        f"- Objetivo: {perfil.objetivo.value}\n\n"
        f"CARTERA RECOMENDADA:\n{pesos_texto}\n\n"
        f"MÉTRICAS:\n"
        f"- Rentabilidad esperada: {resultado['rentabilidad']*100:.1f}%\n"
        f"- Volatilidad: {resultado['volatilidad']*100:.1f}%\n"
        f"- Ratio de Sharpe: {resultado['sharpe']:.2f}\n\n"
        f"JUSTIFICACIÓN DE LAS INCLINACIONES:\n{justificaciones or 'ninguna'}"
        )

    completion = cliente.chat.completions.create(
        model=MODELO_POR_DEFECTO,
        messages=[
            {
                "role": "system",
                "content": (
                    "Eres un asesor financiero que explica una cartera de "
                    "inversión a un cliente sin conocimientos técnicos. Tu "
                    "explicación debe ser clara, honesta y en un tono cercano "
                    "pero profesional.\n\n"
                    "REGLAS:\n"
                    "1. Explica POR QUÉ esta cartera encaja con el perfil.\n"
                    "2. Usa el CONOCIMIENTO DE REFERENCIA para definir los "
                    "conceptos correctamente. No inventes definiciones.\n"
                    "3. Sé honesto sobre el riesgo: no prometas rentabilidades.\n"
                    "4. No des consejos fuera de la cartera presentada.\n"
                    "5. Estructura: una introducción, el porqué de la "
                    "composición, y una nota sobre el riesgo.\n\n"
                    f"CONOCIMIENTO DE REFERENCIA:\n{contexto_rag}"
                )
            },
            {
                "role": "user",
                "content": (
                    f"Explica esta cartera a tu cliente:\n\n{datos}"
                )
            }
        ]
    )
    
    return completion.choices[0].message.content


    