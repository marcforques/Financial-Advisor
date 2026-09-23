# Asesor de inversión — Frontend

Interfaz web (Next.js) del asesor financiero. Consume la API FastAPI del backend.

## Requisitos

- Node.js 18.17 o superior (comprueba con `node --version`).
- El backend FastAPI corriendo (por defecto en `http://127.0.0.1:8001`).

## Puesta en marcha (primera vez)

1. Instala las dependencias (descarga node_modules, solo la primera vez):

   ```bash
   npm install
   ```

2. Comprueba que la URL de la API en `.env.local` es correcta:

   ```
   NEXT_PUBLIC_API_URL=http://127.0.0.1:8001
   ```

3. Arranca el servidor de desarrollo:

   ```bash
   npm run dev
   ```

4. Abre `http://localhost:3000` en el navegador.

## Importante: los dos servidores a la vez

Esta app necesita el backend corriendo en paralelo. Usa dos terminales:

- Terminal 1 (backend, en la carpeta del proyecto Python):
  ```bash
  uvicorn api.main:app --reload
  ```
- Terminal 2 (este frontend):
  ```bash
  npm run dev
  ```

## Estructura

```
asesor-frontend/
├── app/
│   ├── layout.js       Layout raíz (fuente, metadatos)
│   ├── page.js         Página principal (monta el wizard)
│   └── globals.css     Estilos base
├── components/
│   └── WizardCartera.jsx   El asistente de 5 pasos + pantalla de resultado
├── .env.local          URL de la API (punto de conexión con el backend)
├── package.json        Dependencias
└── next.config.mjs     Configuración de Next.js
```

## Arquitectura

Frontend y backend son dos servicios independientes que se comunican por HTTP:

- El frontend (puerto 3001) no contiene lógica de negocio; solo recoge el
  perfil del usuario y muestra la cartera que devuelve la API.
- El backend (puerto 8001) expone la lógica del sistema multiagente.
- El archivo `.env.local` es la costura que los une (la URL de la API).

Este desacoplamiento permite cambiar el frontend sin tocar el backend.
