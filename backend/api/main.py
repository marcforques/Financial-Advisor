"""
API del asesor financiero (FastAPI).

Expone la lógica del sistema (construcción de cartera, rebalanceo) como
endpoints web que el frontend Next.js consume por HTTP. La lógica vive en
los módulos Python existentes (core, agents, orquestador, rebalanceo);
esta capa solo la traduce a peticiones y respuestas web.
"""

import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

from api.modelos import PeticionCartera, RespuestaCartera, ActivoCartera
from api.modelos_auth import UsuarioSesion
from api.rutas_auth import router as router_auth
from api.rutas_cartera import router as router_carteras
from api.seguridad import obtener_usuario_actual, obtener_repositorio
from api.dependencias import obtener_grafo
from api.modelos_cartera import CarteraGuardada, Posicion
from agents.perfil import PerfilInversor
from agents.perfilador import extraer_matices
from universo.catalogo import metadatos
from core.data import descargar_precios, obtener_precios_actuales
from persistencia.repositorio import RepositorioSupabase



app = FastAPI(
    title="Asesor Financiero API",
    description="API del sistema multiagente de asesoramiento de carteras.",
    version="0.1.0",
)

app.include_router(router_auth)
app.include_router(router_carteras)

# CORS: permite que el frontend (en otro puerto/dominio) llame a la API.
# En desarrollo permitimos localhost; en producción se restringe.
def _origenes_cors() -> list[str]:
    """Lee una lista de orígenes separada por comas.

    En local conserva los puertos habituales. En producción se configura
    mediante CORS_ORIGINS, por ejemplo ``https://mi-app.example``.
    """
    valor = os.environ.get("CORS_ORIGINS")
    if valor:
        return [origen.strip().rstrip("/") for origen in valor.split(",") if origen.strip()]
    return [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_origenes_cors(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def raiz():
    """Endpoint de salud: confirma que la API está viva."""
    return {"estado": "ok", "mensaje": "Asesor Financiero API en marcha"}


@app.get("/salud")
def salud():
    """Comprobación de salud más detallada."""
    return {
        "estado": "ok",
        "componentes": {
            "api": "activa",
            "version": "0.1.0",
        }
    }
    

@app.post("/cartera", response_model=RespuestaCartera)
def crear_cartera(
    peticion: PeticionCartera,
    usuario: UsuarioSesion = Depends(obtener_usuario_actual),
    repo: RepositorioSupabase = Depends(obtener_repositorio),
):
    """
    Crea una cartera recomendada a partir de un perfil.

    Recibe el perfil del frontend, ejecuta el grafo de orquestación
    completo (selección de universo, views, optimización, explicación) y
    devuelve la cartera con su explicación.
    """
    
    # Construir el perfil del dominio a partir de la petición.
    matices = []
    if peticion.texto_libre.strip():
        extraidos = extraer_matices(peticion.texto_libre)
        matices = extraidos.matices
        
    perfil = PerfilInversor(
        nivel_riesgo=peticion.nivel_riesgo,
        horizonte_anios=peticion.horizonte_anios,
        capital=peticion.capital,
        objetivo=peticion.objetivo,
        matices=matices
    )    
    
    # Ejecutar el grafo (el sistema selecciona universo, optimiza, explica).
    estado_inicial = {
        "perfil": perfil,
        "universo": [],
        "S": None,
        "market_caps": {},
        "views": None,
        "resultado": None,
        "explicacion": None,
        "perfil_valido": False,
        "mensaje_error": None
    }
    
    grafo = obtener_grafo()
    final = grafo.invoke(estado_inicial)
    
    # Traducir el resultado del dominio a la respuesta de la API.
    resultado = final["resultado"]
    activos = []
    if resultado:
        for ticker, peso in resultado["pesos"].items():
            if peso > 0.001:
                try:
                    region = metadatos(ticker)["region"].value
                except Exception:
                    region=""
                activos.append(ActivoCartera(
                    ticker=ticker,
                    peso=peso,
                    importe=peso * peticion.capital,
                    region=region
                ))
    
    # Guardado automático de la cartera generada.
    cartera_id = None
    if resultado:
        try:
            cartera_id = _guardar_cartera_automatica(
                perfil=perfil,
                resultado=resultado,
                capital=peticion.capital,
                usuario_id=usuario.id,
                nombre=peticion.nombre,
                explicacion=final.get("explicacion", ""),
                repo=repo,
            )
        except Exception as e:
            # Si el guarado falla, no rompemos la respuesta de la cartera.
            print(f"Aviso: no se pudo guardar la cartera automáticamente: {e}")
    
    return RespuestaCartera(
        activos=activos,
        rentabilidad_esperada=resultado["rentabilidad"] if resultado else 0.0,
        volatilidad=resultado["volatilidad"] if resultado else 0.0,
        sharpe=resultado["sharpe"] if resultado else 0.0,
        explicacion=final.get("explicacion", ""),
        universo_considerado=len(final.get("universo", [])),
        cartera_id=cartera_id
    )
    
    
def _guardar_cartera_automatica(perfil, resultado, capital, usuario_id, nombre, explicacion, repo):
    """
    Convierte la cartera generada (pesos) en una CarteraGuardada
    (participaciones + precios de compra) y la persiste.

    Los precios de compra son los precios ACTUALES (se compra hoy). Las
    participaciones se derivan de: peso * capital / precio_actual.
    Guarda también los pesos_objetivo, para el rebalanceo "volver al plan".
    """
    pesos = resultado["pesos"]
    tickers = list(pesos.keys())
    
    # Precio actual de cada activo
    precios_actuales = obtener_precios_actuales(tickers)
    
    # Convertir pesos -> participaciones
    posiciones = []
    for ticker, peso in pesos.items():
        precio = precios_actuales[ticker]
        importe = peso * capital
        participaciones = importe / precio if precio > 0 else 0
        if participaciones > 0: 
            posiciones.append(Posicion(
                ticker=ticker,
                participaciones=participaciones,
                precio_compra=precio
            ))
            
    # Nombre por defecto si no se dio uno.
    if not nombre:
        nombre = f"Cartera {perfil.nivel_riesgo.value} · {datetime.now():%d/%m/%Y}"
    
    cartera = CarteraGuardada(
        usuario_id=usuario_id,
        nombre=nombre,
        posiciones=posiciones,
        nivel_riesgo=perfil.nivel_riesgo,
        horizonte_anios=perfil.horizonte_anios,
        objetivo=perfil.objetivo,
        pesos_objetivo=dict(pesos),
        explicacion=explicacion or None,
    )

    cartera_id = repo.guardar(cartera)
    return cartera_id
    
    
