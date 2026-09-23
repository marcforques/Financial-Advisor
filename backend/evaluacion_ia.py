"""
Evaluación de los componentes basados en LLM del asesor financiero.

Evalúa, cada una en su propia función, cuatro dimensiones:
  1. Precisión del perfilador  (agents/perfilador.py:extraer_matices)
  2. Consistencia/estabilidad del perfilador ante llamadas repetidas
  3. Ausencia de invenciones del explicador (agents/explicador.py:explicar_cartera)
  4. Relevancia de las recuperaciones del RAG (rag/base_conocimiento.py)

Ejecutar con:  python evaluacion_ia.py
Requiere un archivo .env en la raíz del proyecto con OPENAI_API_KEY.

NOTA SOBRE EL ALCANCE DE LAS DIMENSIONES 1 Y 2 (decidido tras explorar el
código real): el único agente del sistema que usa un LLM para "perfilar"
es `extraer_matices`, y solo extrae matices cualitativos (preocupaciones,
preferencias, circunstancias) y un resumen a partir del texto libre
OPCIONAL del usuario. Los campos estructurados del perfil (nivel_riesgo,
horizonte_anios, capital, objetivo) los rellena el usuario en un
formulario (ver WizardCartera.jsx) y en este sistema NUNCA los infiere
un LLM. Por tanto, estas dos dimensiones evalúan la calidad de la
extracción de matices/resumen, no una clasificación de riesgo, horizonte,
capital u objetivo que no existe como componente de IA en el sistema.
"""

import re
import sys
import unicodedata
from collections import Counter

from dotenv import load_dotenv

# En consola de Windows, stdout no siempre usa UTF-8 por defecto y los
# acentos se muestran mal (mojibake). Forzarlo aquí es inofensivo en el
# resto de plataformas.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Cargar las variables de entorno (OPENAI_API_KEY) antes de importar
# cualquier módulo del proyecto que instancie el cliente de OpenAI.
load_dotenv(override=True)

from agents.perfilador import extraer_matices
from agents.explicador import explicar_cartera
from agents.perfil import PerfilInversor, NivelRiesgo, ObjetivoInversion
from agents.llm import MODELO_POR_DEFECTO
from rag.base_conocimiento import BaseConocimiento
from rag.corpus import DOCUMENTOS
from universo.catalogo import CATALOGO


SEPARADOR = "=" * 78


def _normalizar(texto: str) -> str:
    """Minúsculas y sin acentos, para comparar por subcadena de forma robusta
    frente a variaciones ortográficas del LLM (p.ej. 'jubilación'/'jubilacion')."""
    texto = texto.lower()
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c))


# ===========================================================================
# 1) PRECISIÓN DEL PERFILADOR (extraer_matices)
# ===========================================================================
# Cada caso trae un texto libre de un inversor y los "temas" que un buen
# perfilador debería reflejar en sus matices/resumen. Un tema se considera
# detectado si aparece alguna de sus palabras clave (sinónimos/raíces) en el
# texto combinado (matices + resumen). El caso 7 es de control: no aporta
# ninguna circunstancia especial, así que el perfilador NO debería inventar
# preocupaciones.
CASOS_PERFILADO = [
    {
        "texto": "Me preocupa mucho perder dinero, no podría dormir tranquilo "
                 "si mi cartera cae de golpe.",
        "temas_esperados": [
            ("miedo a caídas/pérdidas", ["perder", "perdida", "caida", "caidas", "riesgo"]),
        ],
    },
    {
        "texto": "Necesito tener parte del dinero disponible en cualquier "
                 "momento, por si surge una emergencia médica.",
        "temas_esperados": [
            ("necesidad de liquidez", ["liquidez", "disponible", "emergencia"]),
        ],
    },
    {
        "texto": "Quiero invertir solo en empresas con buenas prácticas "
                 "medioambientales y sociales, nada de petroleras.",
        "temas_esperados": [
            ("inversión ética/sostenible", ["etic", "sostenib", "medioambient", "social", "esg"]),
        ],
    },
    {
        "texto": "Me jubilo dentro de tres años y no quiero sobresaltos con "
                 "mis ahorros.",
        "temas_esperados": [
            ("jubilación próxima", ["jubila"]),
        ],
    },
    {
        "texto": "Tengo dos hijas pequeñas y estoy ahorrando para pagarles "
                 "la universidad dentro de quince años.",
        "temas_esperados": [
            ("ahorro para hijos/educación", ["hij", "educa", "universi"]),
        ],
    },
    {
        "texto": "Voy a recibir una herencia de mis padres y no tengo "
                 "experiencia invirtiendo grandes cantidades.",
        "temas_esperados": [
            ("herencia", ["herencia"]),
            ("falta de experiencia", ["experiencia", "inexpert", "nunca he invertido"]),
        ],
    },
    {
        "texto": "No tengo ninguna circunstancia especial que contar, "
                 "simplemente quiero hacer crecer mis ahorros.",
        "temas_esperados": [],  # caso de control
    },
    {
        "texto": "Soy bastante conservador con el dinero, pero necesito "
                 "guardar una parte para la boda de mi hija el año que viene.",
        "temas_esperados": [
            ("evento vital a corto plazo", ["boda", "corto plazo", "proximo ano", "ano que viene"]),
        ],
    },
]


def evaluar_precision_perfilador() -> dict:
    """
    Para cada caso, llama a extraer_matices() y comprueba si los temas
    esperados aparecen en el texto combinado de matices + resumen.
    Imprime el detalle por caso y la cobertura temática global.
    """
    print(SEPARADOR)
    print("1) PRECISIÓN DEL PERFILADOR (extraer_matices)")
    print(SEPARADOR)

    temas_totales = 0
    temas_detectados = 0
    resultados_casos = []

    for i, caso in enumerate(CASOS_PERFILADO, start=1):
        texto = caso["texto"]
        temas_esperados = caso["temas_esperados"]

        try:
            extraido = extraer_matices(texto)
        except Exception as e:
            print(f"[Caso {i}] ERROR llamando al perfilador: {e}")
            resultados_casos.append({"caso": i, "error": str(e)})
            continue

        texto_generado = _normalizar(" ".join(extraido.matices) + " " + extraido.resumen)

        if not temas_esperados:
            # Caso de control: no debería inventar preocupaciones inexistentes.
            acierto = len(extraido.matices) == 0
            temas_totales += 1
            temas_detectados += int(acierto)
            print(f"[Caso {i}] (control, sin temas esperados) "
                  f"matices generados={len(extraido.matices)} -> "
                  f"{'OK (vacío)' if acierto else 'FALLO (inventó matices)'}")
            resultados_casos.append({
                "caso": i, "control": True, "temas_esperados": 1, "temas_detectados": int(acierto),
            })
            continue

        detectados = 0
        for _nombre_tema, palabras_clave in temas_esperados:
            if any(p in texto_generado for p in palabras_clave):
                detectados += 1

        temas_totales += len(temas_esperados)
        temas_detectados += detectados

        pct = 100 * detectados / len(temas_esperados)
        print(f"[Caso {i}] temas detectados: {detectados}/{len(temas_esperados)} ({pct:.0f}%)")
        print(f"    matices: {extraido.matices}")
        resultados_casos.append({
            "caso": i, "temas_esperados": len(temas_esperados), "temas_detectados": detectados,
        })

    pct_global = 100 * temas_detectados / temas_totales if temas_totales else 0.0
    print(f"\n>> Cobertura temática global: {temas_detectados}/{temas_totales} ({pct_global:.1f}%)")
    return {"pct_global": pct_global, "casos": resultados_casos}


# ===========================================================================
# 2) CONSISTENCIA / ESTABILIDAD DEL PERFILADOR
# ===========================================================================
# Reutiliza tres casos representativos de arriba y repite la misma llamada
# varias veces. Mide si la salida (matices + resumen) es idéntica entre
# repeticiones: un LLM perfectamente determinista daría 100%; valores más
# bajos reflejan el no-determinismo propio de la generación por muestreo.
CASOS_CONSISTENCIA = [CASOS_PERFILADO[0], CASOS_PERFILADO[2], CASOS_PERFILADO[3]]
REPETICIONES = 5


def evaluar_consistencia_perfilador() -> dict:
    print(SEPARADOR)
    print(f"2) CONSISTENCIA DEL PERFILADOR ({REPETICIONES} repeticiones por caso)")
    print(SEPARADOR)
    print("Mide si el perfilador detecta un número estable de matices ante")
    print("el mismo texto. Se compara el número de matices detectados en cada")
    print("repetición, no su redacción literal (que varía por la naturaleza")
    print("generativa del modelo de lenguaje).\n")

    resultados_casos = []
    porcentajes = []

    for i, caso in enumerate(CASOS_CONSISTENCIA, start=1):
        texto = caso["texto"]
        num_matices = []  # número de matices detectados en cada repetición
        errores = 0
        for rep in range(REPETICIONES):
            try:
                extraido = extraer_matices(texto)
                num_matices.append(len(extraido.matices))
            except Exception as e:
                print(f"[Caso {i}] ERROR en repetición {rep + 1}: {e}")
                errores += 1

        if not num_matices:
            print(f"[Caso {i}] Sin resultados válidos (todas las llamadas fallaron).")
            resultados_casos.append({"caso": i, "pct_consistencia": None, "errores": errores})
            continue

        # Consistencia = proporción de repeticiones que coinciden con la moda
        # del número de matices detectados.
        conteo = Counter(num_matices)
        valor_moda, veces_moda = conteo.most_common(1)[0]
        pct = 100 * veces_moda / len(num_matices)
        porcentajes.append(pct)

        print(f"[Caso {i}] \"{texto[:60]}...\"")
        print(f"    números de matices detectados: {num_matices}")
        print(f"    moda: {valor_moda} matices ({veces_moda}/{len(num_matices)} repeticiones), "
              f"consistencia={pct:.0f}%")
        resultados_casos.append({
            "caso": i, "pct_consistencia": pct, "num_matices": num_matices, "errores": errores,
        })

    pct_global = sum(porcentajes) / len(porcentajes) if porcentajes else 0.0
    print(f"\n>> Consistencia media (estabilidad del número de matices): {pct_global:.1f}%")
    return {"pct_global": pct_global, "casos": resultados_casos}

# ===========================================================================
# 3) EXPLICADOR: AUSENCIA DE INVENCIONES / CONTRADICCIONES
# ===========================================================================
# Simula carteras con activos reales del catálogo (evita depender de red
# para descargar precios y ejecutar el optimizador completo) y comprueba
# que la explicación generada no mencione ningún activo del catálogo que
# no forme parte de esa cartera concreta.
CARTERAS_SIMULADAS = [
    {
        "pesos": {"VUSA.AS": 0.40, "SUAG.L": 0.30, "SGLN.L": 0.20, "XMME.DE": 0.10},
        "rentabilidad": 0.071, "volatilidad": 0.118, "sharpe": 0.43,
        "views_usadas": [
            {"activo": "XMME.DE", "justificacion": "Se espera un repunte de los mercados emergentes."},
        ],
    },
    {
        "pesos": {"SUAG.L": 0.55, "ITPS.L": 0.20, "IUSP.AS": 0.15, "XUHC.DE": 0.10},
        "rentabilidad": 0.045, "volatilidad": 0.061, "sharpe": 0.41,
        "views_usadas": [
            {"activo": "XUHC.DE", "justificacion": "El sector salud ofrece defensividad con crecimiento moderado."},
        ],
    },
]

PERFIL_SIMULADO = PerfilInversor(
    nivel_riesgo=NivelRiesgo.MODERADO,
    horizonte_anios=10,
    capital=20000,
    objetivo=ObjetivoInversion.CRECIMIENTO,
)


def _mencionado_en_texto(texto: str, ticker: str, nombre: str) -> bool:
    """
    Comprueba si un activo aparece mencionado en el texto, por su ticker
    (con límites de palabra, para que p.ej. 'IEF' no case dentro de
    'IEAG.AS') o por su nombre completo del catálogo.
    """
    patron_ticker = r"(?<![A-Za-zÁÉÍÓÚÑ0-9])" + re.escape(ticker) + r"(?![A-Za-zÁÉÍÓÚÑ0-9])"
    if re.search(patron_ticker, texto):
        return True
    return _normalizar(nombre) in _normalizar(texto)


def evaluar_explicador_sin_invenciones(kb: BaseConocimiento) -> dict:
    print(SEPARADOR)
    print("3) EXPLICADOR: AUSENCIA DE INVENCIONES")
    print(SEPARADOR)

    catalogo_map = {activo["ticker"]: activo["nombre"] for activo in CATALOGO}
    resultados = []
    total_invenciones = 0
    carteras_limpias = 0
    carteras_evaluadas = 0

    for i, resultado_cartera in enumerate(CARTERAS_SIMULADAS, start=1):
        tickers_cartera = set(resultado_cartera["pesos"].keys())
        print(f"[Cartera {i}] activos: {sorted(tickers_cartera)}")

        try:
            explicacion = explicar_cartera(PERFIL_SIMULADO, resultado_cartera, kb)
        except Exception as e:
            print(f"[Cartera {i}] ERROR llamando al explicador: {e}")
            resultados.append({"cartera": i, "error": str(e)})
            continue

        # Cualquier activo del catálogo que NO esté en la cartera pero
        # aparezca mencionado en el texto es una invención/alucinación.
        invenciones = [
            ticker for ticker, nombre in catalogo_map.items()
            if ticker not in tickers_cartera and _mencionado_en_texto(explicacion, ticker, nombre)
        ]

        carteras_evaluadas += 1
        total_invenciones += len(invenciones)
        carteras_limpias += int(len(invenciones) == 0)

        print(f"    activos inventados: {len(invenciones)} {invenciones if invenciones else ''}")
        resultados.append({
            "cartera": i, "num_invenciones": len(invenciones), "invenciones": invenciones,
        })

    pct_limpias = 100 * carteras_limpias / carteras_evaluadas if carteras_evaluadas else 0.0
    print(f"\n>> Total de activos inventados en {carteras_evaluadas} explicaciones: {total_invenciones}")
    print(f">> Carteras sin invenciones: {carteras_limpias}/{carteras_evaluadas} ({pct_limpias:.1f}%)")
    return {
        "total_invenciones": total_invenciones,
        "pct_carteras_limpias": pct_limpias,
        "carteras": resultados,
    }


# ===========================================================================
# 4) RELEVANCIA DEL RAG
# ===========================================================================
# Una consulta por documento real del corpus (rag/corpus.py). Comprueba si
# el fragmento más relevante que devuelve la base de conocimiento
# corresponde al documento del tema esperado.
CONSULTAS_RAG = [
    {"consulta": "¿Qué es la diversificación de una cartera de inversión?", "id_esperado": "diversificacion"},
    {"consulta": "¿Cómo se calcula el ratio de Sharpe?", "id_esperado": "ratio_sharpe"},
    {"consulta": "¿Qué es el horizonte temporal de una inversión?", "id_esperado": "horizonte_temporal"},
    {"consulta": "¿Qué significa que un activo tenga mucha volatilidad?", "id_esperado": "volatilidad"},
    {"consulta": "¿Qué son los bonos o la renta fija?", "id_esperado": "bonos_renta_fija"},
    {"consulta": "¿Por qué se dice que el oro es un activo refugio?", "id_esperado": "oro_cobertura"},
]


def evaluar_relevancia_rag(kb: BaseConocimiento) -> dict:
    print(SEPARADOR)
    print("4) RELEVANCIA DEL RAG")
    print(SEPARADOR)

    # buscar() solo devuelve el texto, no el id/categoría; reconstruimos el
    # id a partir del texto exacto guardado en el corpus.
    texto_a_id = {doc["texto"]: doc["id"] for doc in DOCUMENTOS}

    aciertos = 0
    total = 0
    detalle = []

    for caso in CONSULTAS_RAG:
        consulta = caso["consulta"]
        id_esperado = caso["id_esperado"]
        try:
            fragmentos = kb.buscar(consulta, n_resultados=1)
        except Exception as e:
            print(f"[RAG] ERROR consultando \"{consulta}\": {e}")
            detalle.append({"consulta": consulta, "error": str(e)})
            continue

        id_obtenido = texto_a_id.get(fragmentos[0]) if fragmentos else None
        acierto = id_obtenido == id_esperado
        aciertos += int(acierto)
        total += 1

        print(f"[RAG] \"{consulta}\"")
        print(f"    esperado={id_esperado}  obtenido={id_obtenido}  -> {'OK' if acierto else 'FALLO'}")
        detalle.append({
            "consulta": consulta, "esperado": id_esperado, "obtenido": id_obtenido, "acierto": acierto,
        })

    pct = 100 * aciertos / total if total else 0.0
    print(f"\n>> Recuperaciones relevantes: {aciertos}/{total} ({pct:.1f}%)")
    return {"pct_relevancia": pct, "detalle": detalle}


# ===========================================================================
# ORQUESTACIÓN Y RESUMEN
# ===========================================================================
def main():
    print(SEPARADOR)
    print("EVALUACIÓN DE LOS COMPONENTES DE IA DEL ASESOR FINANCIERO")
    print(f"Modelo LLM: {MODELO_POR_DEFECTO}")
    print(SEPARADOR)

    resultado_precision = evaluar_precision_perfilador()
    resultado_consistencia = evaluar_consistencia_perfilador()

    # La base de conocimiento se construye una sola vez y se reutiliza en
    # las dimensiones 3 y 4, igual que hace la API (api/dependencias.py).
    resultado_explicador = {"total_invenciones": None, "pct_carteras_limpias": None}
    resultado_rag = {"pct_relevancia": None}
    try:
        kb = BaseConocimiento()
        kb.añadir_documentos(DOCUMENTOS)
    except Exception as e:
        print(SEPARADOR)
        print(f"ERROR construyendo la base de conocimiento, se omiten las dimensiones 3 y 4: {e}")
    else:
        try:
            resultado_explicador = evaluar_explicador_sin_invenciones(kb)
        except Exception as e:
            print(f"ERROR en la evaluación del explicador: {e}")
        try:
            resultado_rag = evaluar_relevancia_rag(kb)
        except Exception as e:
            print(f"ERROR en la evaluación del RAG: {e}")

    # ---- Resumen final: tabla lista para pegar en una memoria académica ----
    print("\n" + SEPARADOR)
    print("RESUMEN FINAL")
    print(SEPARADOR)

    def _fmt_pct(valor):
        return f"{valor:.1f}%" if valor is not None else "N/D"

    filas = [
        ("Dimensión", "Métrica"),
        ("1. Cobertura temática del perfilador", _fmt_pct(resultado_precision["pct_global"])),
        (f"2. Consistencia del perfilador ({REPETICIONES} repet.)", _fmt_pct(resultado_consistencia["pct_global"])),
        ("3. Carteras del explicador sin invenciones", _fmt_pct(resultado_explicador["pct_carteras_limpias"])),
        ("3b. Activos inventados (total)", str(resultado_explicador["total_invenciones"])
                                            if resultado_explicador["total_invenciones"] is not None else "N/D"),
        ("4. Relevancia de recuperación del RAG", _fmt_pct(resultado_rag["pct_relevancia"])),
    ]

    ancho_1 = max(len(f[0]) for f in filas) + 2
    print(f"| {filas[0][0]:<{ancho_1}}| {filas[0][1]}")
    print(f"|{'-' * (ancho_1 + 1)}|{'-' * 12}")
    for nombre, valor in filas[1:]:
        print(f"| {nombre:<{ancho_1}}| {valor}")
    print(SEPARADOR)


if __name__ == "__main__":
    main()
