# Despliegue a producción

La aplicación consta de dos servicios: el frontend Next.js y la API FastAPI.
Supabase sigue siendo el servicio de autenticación y persistencia.

## Variables necesarias

Backend:

- `OPENAI_API_KEY`
- `RAG_EMBEDDING_MODEL` (opcional; por defecto `text-embedding-3-small`)
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY` (nunca la clave `service_role`)
- `CORS_ORIGINS`: URL pública exacta del frontend, sin barra final. Admite
  varias URLs separadas por comas.

Frontend (se fija durante la compilación):

- `NEXT_PUBLIC_API_URL`: URL HTTPS pública del backend, sin barra final.

## Comprobación local con Docker

1. Copia `.env.example` a `.env` y sustituye los valores. No subas `.env`
   al repositorio.
2. Ejecuta `docker compose up --build`.
3. Comprueba `http://localhost:8001/salud` y abre
   `http://localhost:3000`.

## Publicación

Publica cada carpeta como un servicio Docker independiente. En el backend,
configura las cuatro variables indicadas y un volumen persistente montado en
`/app/data` para la caché de mercado. En el frontend, pasa
`NEXT_PUBLIC_API_URL` como argumento de compilación.

Orden recomendado:

1. Publica el backend y verifica `https://URL-API/salud`.
2. Compila/publica el frontend usando esa URL en `NEXT_PUBLIC_API_URL`.
3. Añade la URL pública del frontend a `CORS_ORIGINS` en el backend y
   reinícialo.
4. En Supabase, configura las URLs permitidas para autenticación y verifica
   que la tabla `carteras` tiene RLS activo y políticas por `auth.uid()`.

La API realiza llamadas externas a OpenAI, Yahoo Finance y Supabase. Configura
timeouts y alertas en la plataforma y usa al menos 1 GB de RAM (2 GB resulta
más holgado para la optimización numérica).
