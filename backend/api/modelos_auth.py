"""
Modelos de petición y respuesta de autenticación.

Mismo patrón que api/modelos.py: Pydantic valida lo que entra y da forma a
lo que sale. El "usuario" que se devuelve es el objeto mínimo que el
frontend necesita (id + email), no el User completo de Supabase.
"""

from pydantic import BaseModel, EmailStr, Field


class PeticionRegistro(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, description="Mínimo 8 caracteres.")


class PeticionLogin(BaseModel):
    email: EmailStr
    password: str


class UsuarioSesion(BaseModel):
    id: str
    email: str


class RespuestaSesion(BaseModel):
    """Lo que devuelven /auth/registro y /auth/login."""
    access_token: str
    refresh_token: str
    expires_at: int | None = None
    usuario: UsuarioSesion
