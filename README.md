# Financial Advisor

TFM de asesoramiento financiero con generación y rebalanceo de carteras.

- `frontend/`: interfaz Next.js desplegable en Vercel.
- `backend/`: API FastAPI desplegable en Railway mediante Docker.
- Supabase: autenticación y persistencia.
- OpenAI: perfilado, views, explicación y embeddings del RAG.

## Desarrollo local

Consulta [PRODUCCION.md](PRODUCCION.md) para las variables necesarias y el
despliegue. Con Docker:

```bash
cp .env.example .env
docker compose up --build
```

Frontend: <http://localhost:3000>. API: <http://localhost:8001/salud>.

## Verificación

```bash
cd backend && pytest -q
cd frontend && npm ci && npm run build
```
