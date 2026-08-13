"""
Base de conocimiento (fachada sobre el motor vectorial).

Responsabilidad única: ofrecer una interfaz simple para almacenar y
buscar documentos por similitud semántica, ocultando el motor concreto
(ChromaDB) que hay debajo.
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
        """
        # Modelo de embeddings multilingüe: entiende español mucho mejor que el por defecto
        funcion_embedding = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="paraphrase-multilingual-MiniLM-L12-v2"
        )
        
        
        # Cliente en memoria: rápido y sin persistencia en disco.
        self._cliente = chromadb.Client()
        self._coleccion = self._cliente.get_or_create_collection(
            name=nombre_coleccion,
            embedding_function=funcion_embedding
            )
        
    
    def añadir_documentos(self, documentos: list[dict]) -> None:
        """
        Añade documentos a la base de conocimiento.
        """
        self._coleccion.add(
            ids=[doc["id"] for doc in documentos],
            documents=[doc["texto"] for doc in documentos],
            metadatas=[{"categoria": doc["categoria"]} for doc in documentos]
        )
        
    
    def buscar(self, consulta: str, n_resultados: int = 2) -> list[str]:
        """
        Busca los documentos más relevantes para una consulta.
        """
        resultado = self._coleccion.query(
            query_texts=[consulta],
            n_results=n_resultados
        )
        # extraemos los textos.
        return resultado["documents"][0]