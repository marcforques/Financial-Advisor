"""
Repositorio de carteras (patrón repositorio).

Define la interfaz de almacenamiento de carteras y su implementación con
SQLite. El resto del sistema usa SOLO la interfaz, sin saber qué motor hay
debajo. Así, migrar a Supabase al final es cambiar la implementación sin
tocar nada más.

Mismo patrón de fachada usado en el catálogo y en la base de conocimiento:
aislar la dependencia externa tras una interfaz estable.
"""

import os
import json
import sqlite3
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from supabase import create_client

from api.modelos_cartera import CarteraGuardada, Posicion

class RepositorioCarteras(ABC):
    """
    Interfaz de un repositorio de carteras.

    Cualquier implementación (SQLite, Supabase, ...) debe ofrecer estos
    métodos. El sistema depende de esta interfaz, no de la implementación.
    """

    @abstractmethod
    def guardar(self, cartera: CarteraGuardada) -> str:
        """Guarda una cartera y devuelve su id."""
        ...

    @abstractmethod
    def obtener(self, cartera_id: str) -> CarteraGuardada | None:
        """Recupera una cartera por su id, o None si no existe."""
        ...

    @abstractmethod
    def listar_por_usuario(self, usuario_id: str) -> list[CarteraGuardada]:
        """Lista todas las carteras de un usuario."""
        ...

    @abstractmethod
    def eliminar(self, cartera_id: str) -> bool:
        """Elimina una cartera. Devuelve True si existía."""
        ...
        
        
class RepositorioSQLite(RepositorioCarteras):
    """
    Implementación del repositorio con SQLite (base de datos local).
    """

    def __init__(self, ruta_db: str = "carteras.db"):
        self.ruta_db = ruta_db
        self._crear_tabla()

    def _conectar(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.ruta_db)
        conn.row_factory = sqlite3.Row  # acceso por nombre de columna
        return conn

    def _crear_tabla(self) -> None:
        """
        Crea la tabla de carteras si no existe.
        """
        with self._conectar() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS carteras (
                    id TEXT PRIMARY KEY,
                    usuario_id TEXT NOT NULL,
                    nombre TEXT NOT NULL,
                    posiciones TEXT NOT NULL,
                    nivel_riesgo TEXT NOT NULL,
                    horizonte_anios INTEGER NOT NULL,
                    objetivo TEXT NOT NULL,
                    fecha_creacion TEXT NOT NULL,
                    es_externa INTEGER NOT NULL,
                    pesos_objetivo TEXT,
                    explicacion TEXT
                )
            """)
            # Migración para bases de datos creadas antes de añadir la
            # columna: CREATE TABLE IF NOT EXISTS no toca una tabla que ya
            # existe, así que en una carteras.db previa a este cambio la
            # columna seguiría sin existir. Se intenta añadir y se ignora
            # el error si ya está (sqlite no tiene "ADD COLUMN IF NOT
            # EXISTS").
            try:
                conn.execute("ALTER TABLE carteras ADD COLUMN explicacion TEXT")
            except sqlite3.OperationalError:
                pass  # la columna ya existe

    def guardar(self, cartera: CarteraGuardada) -> str:
        """
        Guarda una cartera (inserta o actualiza) y devuelve su id.
        """
        import uuid
        if cartera.id is None:
            cartera.id = str(uuid.uuid4())

        # Las posiciones se serializan a JSON para guardarlas en una columna.
        posiciones_json = json.dumps([p.model_dump() for p in cartera.posiciones])

        objetivo_json = (
            json.dumps(cartera.pesos_objetivo)
            if cartera.pesos_objetivo is not None else None
        )

        with self._conectar() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO carteras
                (id, usuario_id, nombre, posiciones, nivel_riesgo,
                 horizonte_anios, objetivo, fecha_creacion, es_externa,
                 pesos_objetivo, explicacion)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cartera.id,
                cartera.usuario_id,
                cartera.nombre,
                posiciones_json,
                cartera.nivel_riesgo.value,
                cartera.horizonte_anios,
                cartera.objetivo.value,
                cartera.fecha_creacion.isoformat(),
                int(cartera.es_externa),
                objetivo_json,
                cartera.explicacion
            ))
        return cartera.id
    
    def _fila_a_cartera(self, fila: sqlite3.Row) -> CarteraGuardada:
        """
        Convierte una fila de la base de datos en un objeto CarteraGuardada.
        """
        posiciones = [
            Posicion(**p) for p in json.loads(fila["posiciones"])
        ]
        
        objetivo = fila["pesos_objetivo"]
        pesos_objetivo = json.loads(objetivo) if objetivo else None
        
        return CarteraGuardada(
            id=fila["id"],
            usuario_id=fila["usuario_id"],
            nombre=fila["nombre"],
            posiciones=posiciones,
            nivel_riesgo=fila["nivel_riesgo"],
            horizonte_anios=fila["horizonte_anios"],
            objetivo=fila["objetivo"],
            fecha_creacion=fila["fecha_creacion"],
            es_externa=bool(fila["es_externa"]),
            pesos_objetivo=pesos_objetivo,
            explicacion=fila["explicacion"]
        )

    def obtener(self, cartera_id: str) -> CarteraGuardada | None:
        with self._conectar() as conn:
            fila = conn.execute(
                "SELECT * FROM carteras WHERE id = ?", (cartera_id,)
            ).fetchone()
        return self._fila_a_cartera(fila) if fila else None

    def listar_por_usuario(self, usuario_id: str) -> list[CarteraGuardada]:
        with self._conectar() as conn:
            filas = conn.execute(
                "SELECT * FROM carteras WHERE usuario_id = ? ORDER BY fecha_creacion DESC",
                (usuario_id,),
            ).fetchall()
        return [self._fila_a_cartera(f) for f in filas]

    def eliminar(self, cartera_id: str) -> bool:
        with self._conectar() as conn:
            cursor = conn.execute(
                "DELETE FROM carteras WHERE id = ?", (cartera_id,)
            )
        return cursor.rowcount > 0
    

class RepositorioSupabase(RepositorioCarteras):
    """
    Implementación del repositorio con Supabase (PostgreSQL en la nube).

    Misma interfaz que RepositorioSQLite: el resto del sistema no distingue
    cuál se usa. Esta es la ventaja del patrón repositorio — migrar de SQLite
    a Supabase es cambiar qué clase se instancia, sin tocar la lógica.

    Se instancia CON el access_token del usuario de la petición (ver
    api/seguridad.py: obtener_repositorio), nunca compartida entre
    peticiones. Con la clave anon + ese token, Postgres resuelve
    auth.uid() como el usuario dueño del token, y las políticas RLS de la
    tabla `carteras` filtran cada consulta por él automáticamente. Sin
    token (por ejemplo en un script/test local), el cliente queda
    autenticado como "anon": las políticas RLS no dejarán ver ni escribir
    nada, así que para uso interactivo hace falta pasar el token.
    """

    def __init__(self, access_token: str | None = None):
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_ANON_KEY")
        if not url or not key:
            raise ValueError("Faltan SUPABASE_URL o SUPABASE_ANON_KEY en las variables de entorno.")

        self.cliente = create_client(url, key)
        if access_token:
            # A partir de aquí, toda petición de este cliente lleva el JWT
            # del usuario: RLS ve auth.uid() = su id, no un acceso anónimo.
            self.cliente.postgrest.auth(access_token)
        self.tabla = "carteras"


    def guardar(self, cartera: CarteraGuardada) -> str:
        """
        Guarda una cartera (inserta o actualiza) y devuelve su id.
        """
        # Antes: cartera_id solo se asignaba dentro del "if cartera.id is
        # None", así que actualizar una cartera existente (con id) hacía
        # que la línea de abajo usara una variable inexistente
        # (UnboundLocalError). Se asigna siempre.
        if cartera.id is None:
            cartera.id = str(uuid.uuid4())
        cartera_id = cartera.id

        # Serializamos posiciones y pesos_objetivos a estructuras JSON.
        fila = {
            "id": cartera_id,
            "usuario_id": cartera.usuario_id,
            "nombre": cartera.nombre,
            "posiciones": [p.model_dump() for p in cartera.posiciones],
            "nivel_riesgo": cartera.nivel_riesgo.value,
            "horizonte_anios": cartera.horizonte_anios,
            "objetivo": cartera.objetivo.value,
            "fecha_creacion": cartera.fecha_creacion.isoformat(),
            "es_externa": cartera.es_externa,
            "pesos_objetivo": cartera.pesos_objetivo,
            "explicacion": cartera.explicacion
            }
        
        respuesta = self.cliente.table(self.tabla).upsert(fila).execute()
        
        if respuesta.data:
            return respuesta.data[0]["id"]
        return cartera.id


    def _fila_a_cartera(self, fila: dict) -> CarteraGuardada:
        """
        Convierte una fila de Supabase en un objeto CarteraGuardada.
        """
        posiciones = [Posicion(**p) for p in fila["posiciones"]]
        return CarteraGuardada(
            id=fila["id"],
            usuario_id=fila["usuario_id"],
            nombre=fila["nombre"],
            posiciones=posiciones,
            nivel_riesgo=fila["nivel_riesgo"],
            horizonte_anios=fila["horizonte_anios"],
            objetivo=fila["objetivo"],
            fecha_creacion=fila["fecha_creacion"],
            es_externa=fila["es_externa"],
            pesos_objetivo=fila.get("pesos_objetivo"),
            explicacion=fila.get("explicacion")
        )
    
    
    def obtener(self, cartera_id: str) -> CarteraGuardada | None:
        respuesta = (
            self.cliente.table(self.tabla)
            .select("*")
            .eq("id", cartera_id)
            .execute()
            )
        
        if not respuesta.data:
            return None
        
        return self._fila_a_cartera(respuesta.data[0])
    
    
    def listar_por_usuario(self, usuario_id) -> list[CarteraGuardada]: 
        respuesta = (
            self.cliente.table(self.tabla)
            .select("*")
            .eq("usuario_id", usuario_id)
            .order("fecha_creacion", desc=True)
            .execute()
        )
        
        return [self._fila_a_cartera(f) for f in respuesta.data]
    

    def eliminar(self, cartera_id: str) -> bool:
        respuesta = (
            self.cliente.table(self.tabla)
            .delete()
            .eq("id", cartera_id)
            .execute()
        )
        
        return len(respuesta.data) > 0