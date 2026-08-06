"""
Corpus de conocimiento financiero para el RAG.

Base de documentos fiables que el agente explicador usa como fuente para
sus explicaciones, evitando que el LLM invente conceptos financieros.

Cada documento tiene un id, una categoría (para poder filtrar en el
futuro) y el texto. En un sistema en producción este corpus viviría en
ficheros o una base de datos; aquí lo mantenemos en código por simplicidad
y reproducibilidad.
"""

DOCUMENTOS = [
    {
        "id": "diversificacion",
        "categoria": "conceptos",
        "texto": (
            "La diversificación consiste en repartir la inversión entre "
            "activos que no se mueven igual entre sí. Cuando los activos "
            "tienen baja correlación, las caídas de unos se compensan con "
            "la estabilidad o subidas de otros, reduciendo el riesgo total "
            "de la cartera sin sacrificar necesariamente rentabilidad. Es el "
            "principio de no poner todos los huevos en la misma cesta."
        ),
    },
    {
        "id": "ratio_sharpe",
        "categoria": "metricas",
        "texto": (
            "El ratio de Sharpe mide la rentabilidad obtenida por cada "
            "unidad de riesgo asumida. Se calcula como la rentabilidad que "
            "supera al activo sin riesgo dividida entre la volatilidad. Un "
            "Sharpe más alto indica mejor relación entre lo que se gana y el "
            "riesgo que se corre. Valores por encima de 1 se consideran "
            "buenos; por debajo de 0,5, mediocres."
        ),
    },
    {
        "id": "horizonte_temporal",
        "categoria": "conceptos",
        "texto": (
            "El horizonte temporal es el tiempo durante el cual se mantiene "
            "la inversión. Cuanto más largo es el horizonte, mayor riesgo se "
            "puede asumir, porque hay más tiempo para recuperarse de caídas "
            "temporales del mercado. Por eso un inversor joven con décadas "
            "por delante puede permitirse más renta variable que alguien "
            "cercano a necesitar el dinero."
        ),
    },
    {
        "id": "volatilidad",
        "categoria": "metricas",
        "texto": (
            "La volatilidad mide cuánto oscilan las rentabilidades de un "
            "activo respecto a su media. Una volatilidad alta significa "
            "movimientos bruscos, tanto al alza como a la baja. Es la medida "
            "de riesgo más usada, aunque no distingue entre subidas y "
            "bajadas. Los bonos suelen tener baja volatilidad; la renta "
            "variable y las materias primas, más alta."
        ),
    },
    {
        "id": "bonos_renta_fija",
        "categoria": "activos",
        "texto": (
            "Los bonos, o renta fija, son préstamos a gobiernos o empresas "
            "que pagan intereses. Se consideran activos defensivos porque su "
            "valor fluctúa menos que las acciones. Aportan estabilidad a la "
            "cartera y suelen comportarse de forma distinta a la bolsa, lo "
            "que ayuda a diversificar. Su rentabilidad esperada es menor que "
            "la de la renta variable a cambio de menor riesgo."
        ),
    },
    {
        "id": "oro_cobertura",
        "categoria": "activos",
        "texto": (
            "El oro se considera un activo refugio y una cobertura frente a "
            "la inflación. Históricamente tiende a mantener su valor cuando "
            "los precios suben o cuando hay incertidumbre en los mercados. "
            "Su correlación con la bolsa suele ser baja, por lo que aporta "
            "diversificación, aunque su rentabilidad a largo plazo es más "
            "irregular que la de la renta variable."
        )
    }
]