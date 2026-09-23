"""
Seguridad: validación del JWT de Supabase y construcción de un repositorio
de carteras autenticado como el usuario de la petición.

Tres dependencias de FastAPI, encadenadas:
  1. obtener_token          -> saca el Bearer token de la cabecera Authorization.
  2. obtener_usuario_actual -> valida ese token contra Supabase Auth, devuelve
                                quién es (id, email). 401 si no es válido.
  3. obtener_repositorio    -> crea un RepositorioSupabase NUEVO, autenticado
                                con ESE token, para que Postgres aplique RLS
                                como ese usuario (auth.uid() = su id).

IMPORTANTE: el repositorio NO es un singleton compartido entre peticiones.
Si lo fuera, con FastAPI sirviendo peticiones concurrentes, el token de un
usuario podría acabar usándose en la consulta de otro (condición de
carrera sobre el mismo cliente HTTP). Una instancia nueva por petición es
barata (no hace red al crearse) y evita ese problema de raíz.

Usamos la clave "anon" (pública) para el cliente base, nunca la
"service_role": con la service_role, Postgres salta RLS por completo y el
filtrado por usuario dependería solo de que el código de la aplicación no
se equivoque nunca. Con la anon key, si alguna ruta olvida adjuntar el
token del usuario, la consulta falla por permisos en vez de devolver datos
de otra persona.
"""

import os

from fastapi import Depends, Header, HTTPException
from supabase import create_client, Client

from api.modelos_auth import UsuarioSesion
from persistencia.repositorio import RepositorioSupabase


def cliente_base() -> Client:
    """
    Cliente de Supabase con la clave anon, sin token de usuario todavía.
    Se usa para validar tokens (auth.get_user) y para registro/login, que
    Supabase espera que se llamen con la clave anon.
    """
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError(
            "Faltan SUPABASE_URL o SUPABASE_ANON_KEY en las variables de entorno."
        )
    return create_client(url, key)


def obtener_token(authorization: str | None = Header(default=None)) -> str:
    """
    Extrae el token de "Authorization: Bearer <token>".
    401 si la cabecera falta o no tiene el formato esperado.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Falta el token de autenticación (cabecera Authorization).",
        )
    return authorization.removeprefix("Bearer ").strip()


def obtener_usuario_actual(token: str = Depends(obtener_token)) -> UsuarioSesion:
    """
    Valida el token contra Supabase Auth (llamada de red: Supabase
    comprueba la firma, la caducidad y que el usuario sigue existiendo) y
    devuelve quién es.

    Usar auth.get_user() en vez de verificar la firma del JWT a mano es
    deliberado: nos independiza de si el proyecto firma con un secreto
    compartido (HS256) o con claves asimétricas (JWKS), y de que roten esa
    clave. El coste es una llamada de red extra por petición protegida;
    para el volumen de esta aplicación es irrelevante.
    """
    cliente = cliente_base()
    try:
        respuesta = cliente.auth.get_user(token)
    except Exception:
        respuesta = None

    if respuesta is None or respuesta.user is None:
        raise HTTPException(
            status_code=401,
            detail="Token inválido o caducado. Inicia sesión de nuevo.",
        )

    return UsuarioSesion(id=respuesta.user.id, email=respuesta.user.email)


def obtener_repositorio(token: str = Depends(obtener_token)) -> RepositorioSupabase:
    """
    Repositorio de carteras autenticado con el token de ESTA petición.
    Con la clave anon + este token, Postgres ve auth.uid() = id del
    usuario, y las políticas RLS filtran solas.
    """
    return RepositorioSupabase(access_token=token)
