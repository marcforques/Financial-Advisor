"""
Endpoints de autenticación (registro, login, refresco de sesión).

Hablan con Supabase Auth a través de supabase-py, con la clave anon (la
que Supabase espera para estas operaciones). No hay estado propio aquí:
Supabase es la única fuente de verdad de usuarios y contraseñas.
"""

from fastapi import APIRouter, HTTPException
from supabase_auth.errors import AuthApiError

from api.modelos_auth import (
    PeticionRegistro,
    PeticionLogin,
    RespuestaSesion,
    UsuarioSesion,
)
from api.seguridad import cliente_base

router = APIRouter(prefix="/auth", tags=["auth"])


def _respuesta_desde_auth(auth_response) -> RespuestaSesion:
    """
    Traduce la respuesta de supabase-py (sign_up / sign_in_with_password,
    que devuelven ambas .session y .user) a nuestro formato de API.
    """
    sesion = auth_response.session
    usuario = auth_response.user
    return RespuestaSesion(
        access_token=sesion.access_token,
        refresh_token=sesion.refresh_token,
        expires_at=sesion.expires_at,
        usuario=UsuarioSesion(id=usuario.id, email=usuario.email),
    )


@router.post("/registro", response_model=RespuestaSesion)
def registro(peticion: PeticionRegistro):
    cliente = cliente_base()
    try:
        respuesta = cliente.auth.sign_up({
            "email": peticion.email,
            "password": peticion.password,
        })
    except AuthApiError as e:
        if e.code in ("email_exists", "user_already_exists"):
            raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese email.")
        if e.code == "weak_password":
            raise HTTPException(status_code=400, detail="La contraseña es demasiado débil.")
        raise HTTPException(status_code=400, detail=e.message)

    if respuesta.session is None:
        # Solo pasa si el proyecto exige confirmación por email: el usuario
        # se crea pero no hay sesión hasta que confirme. Con auto-confirm
        # activado en el proyecto, esto no debería ocurrir nunca; si te
        # aparece, revisa Authentication > Providers > Email > "Confirm
        # email" en el panel de Supabase.
        raise HTTPException(
            status_code=400,
            detail="Cuenta creada. Confirma tu email antes de iniciar sesión.",
        )

    return _respuesta_desde_auth(respuesta)


@router.post("/login", response_model=RespuestaSesion)
def login(peticion: PeticionLogin):
    cliente = cliente_base()
    try:
        respuesta = cliente.auth.sign_in_with_password({
            "email": peticion.email,
            "password": peticion.password,
        })
    except AuthApiError as e:
        if e.code == "invalid_credentials":
            raise HTTPException(status_code=401, detail="Email o contraseña incorrectos.")
        raise HTTPException(status_code=400, detail=e.message)

    return _respuesta_desde_auth(respuesta)


@router.post("/refresh", response_model=RespuestaSesion)
def refrescar(refresh_token: str):
    """
    Cambia un refresh_token por una sesión nueva. El frontend actual no la
    llama automáticamente (no hay refresco silencioso implementado): si el
    access_token caduca, el usuario vuelve a iniciar sesión. Queda lista
    por si más adelante se añade refresco silencioso en el cliente.
    """
    cliente = cliente_base()
    try:
        respuesta = cliente.auth.refresh_session(refresh_token)
    except AuthApiError:
        raise HTTPException(
            status_code=401,
            detail="No se pudo refrescar la sesión, inicia sesión de nuevo.",
        )

    return _respuesta_desde_auth(respuesta)
