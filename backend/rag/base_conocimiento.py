"""
Base de conocimiento ligera con embeddings de OpenAI.

Responsabilidad única: ofrecer una interfaz simple para almacenar y
buscar documentos por similitud semántica sin mantener un servidor vectorial.
"""

import os

import numpy as np
from openai import OpenAI

class BaseConocimiento:
    """
    Almacén de documentos con búsqueda por similitud semántica.
    """

    def __init__(self, nombre_coleccion: str = "conocimiento_financiero"):
        """
        Inicializa la base de conocimiento en memoria.
        """
        clave = os.environ.get("OPENAI_API_KEY")
        if not clave:
            raise ValueError("Falta OPENAI_API_KEY para generar los embeddings del RAG.")
        self._cliente = OpenAI(api_key=clave)
        self._modelo = os.environ.get("RAG_EMBEDDING_MODEL", "text-embedding-3-small")
        self._documentos: list[dict] = []
        self._vectores: np.ndarray | None = None


    def añadir_documentos(self, documentos: list[dict]) -> None:
        """
        Añade documentos a la base de conocimiento.
        """
        if not documentos:
            return
        respuesta = self._cliente.embeddings.create(
            model=self._modelo,
            input=[doc["texto"] for doc in documentos],
        )
        nuevos_vectores = np.asarray(
            [elemento.embedding for elemento in respuesta.data], dtype=float
        )
        self._documentos.extend(documentos)
        self._vectores = (
            nuevos_vectores
            if self._vectores is None
            else np.vstack([self._vectores, nuevos_vectores])
        )


    def buscar(self, consulta: str, n_resultados: int = 2) -> list[str]:
        """
        Busca los documentos más relevantes para una consulta.
        """
        if self._vectores is None or not self._documentos:
            return []

        respuesta = self._cliente.embeddings.create(
            model=self._modelo,
            input=[consulta],
        )
        consulta_vector = np.asarray(respuesta.data[0].embedding, dtype=float)
        denominadores = np.linalg.norm(self._vectores, axis=1) * np.linalg.norm(consulta_vector)
        similitudes = np.divide(
            self._vectores @ consulta_vector,
            denominadores,
            out=np.zeros(len(self._vectores)),
            where=denominadores != 0,
        )
        indices = np.argsort(similitudes)[::-1][:n_resultados]
        return [self._documentos[i]["texto"] for i in indices]
