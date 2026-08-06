"""
Base de conocimiento (fachada sobre el motor vectorial).

Responsabilidad única: ofrecer una interfaz simple para almacenar y
buscar documentos por similitud semántica, ocultando el motor concreto
(ChromaDB) que hay debajo.

DECISIÓN DE DISEÑO: el resto del sistema (el explicador) usa SOLO los
métodos de esta clase. Nunca habla con ChromaDB directamente. Así, si en
el futuro se cambia ChromaDB por otro motor (numpy, Pinecone, etc.), solo
se toca este archivo. Es el mismo patrón de fachada usado en analysis.py
con PyPortfolioOpt.
"""

import chromadb
from chromadb.utils import embedding_functions

class BaseConocimiento:
    """
    Almacén de documentos con búsqueda por similitud semántica.
    """
    
    def __init__(self, nombre_coleccion: str = "conocimiento_financiero"):
        """
        Inicializa la base de conocimiento en memoria.

        Parameters
        ----------
        nombre_coleccion : str
            Nombre de la colección de documentos dentro del motor.
        """
        # Modelo de embeddings multilingüe: entiende español mucho mejor que el por defecto
        funcion_embedding = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="paraphrase-multilingual-MiniLM-L12-v2"
        )
        
        
        # Cliente en memoria: rápido y sin persistencia en disco.
        # Para persistencia se usaría chromadb.PersistentClient(path=)
        self._cliente = chromadb.Client()
        self._coleccion = self._cliente.get_or_create_collection(
            name=nombre_coleccion,
            embedding_function=funcion_embedding
            )
        
    
    def añadir_documentos(self, documentos: list[dict]) -> None:
        """
        Añade documentos a la base de conocimiento.

        Parameters
        ----------
        documentos : list[dict]
            Cada dict debe tener "id", "categoria" y "texto".
        """
        self._coleccion.add(
            ids=[doc["id"] for doc in documentos],
            documents=[doc["texto"] for doc in documentos],
            metadatas=[{"categoria": doc["categoria"]} for doc in documentos]
        )
        
    
    def buscar(self, consulta: str, n_resultados: int = 2) -> list[str]:
        """
        Busca los documentos más relevantes para una consulta.

        Parameters
        ----------
        consulta : str
            Texto de la búsqueda (p. ej. "qué es la diversificación").
        n_resultados : int
            Número de documentos a devolver.

        Returns
        -------
        list[str]
            Textos de los documentos más relevantes, ordenados por
            similitud.
        """
        resultado = self._coleccion.query(
            query_texts=[consulta],
            n_results=n_resultados
        )
        # ChromaDB devuelve una estructura anidada; extraemos los textos.
        return resultado["documents"][0]