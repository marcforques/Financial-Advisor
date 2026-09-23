"use client";

/**
 * lib/auth.js — sesión del usuario en el frontend.
 *
 * El frontend NUNCA habla directamente con Supabase: todo pasa por la API
 * de FastAPI (POST /auth/login, POST /auth/registro), que es quien llama a
 * Supabase Auth y devuelve un access_token (JWT). Este módulo solo:
 *   - guarda/lee esa sesión en localStorage,
 *   - adjunta el token como cabecera Authorization en las llamadas a la API,
 *   - detecta un 401 (token inválido o caducado) y fuerza el re-login,
 *   - expone un hook para proteger páginas que requieren sesión.
 *
 * localStorage es suficiente aquí: es una demo de TFM de una sola pestaña,
 * no una app multi-dispositivo con necesidades de sincronización.
 */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const CLAVE_SESION = "asesor_sesion";

/**
 * Guarda la sesión devuelta por /auth/login o /auth/registro.
 * Forma esperada: { access_token, refresh_token, expires_at, usuario: { id, email } }
 */
export function guardarSesion(sesion) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(CLAVE_SESION, JSON.stringify(sesion));
  } catch {
    // localStorage puede fallar (modo privado, cuota); no es crítico aquí.
  }
}

export function obtenerSesion() {
  if (typeof window === "undefined") return null;
  try {
    const crudo = localStorage.getItem(CLAVE_SESION);
    return crudo ? JSON.parse(crudo) : null;
  } catch {
    return null;
  }
}

export function obtenerToken() {
  return obtenerSesion()?.access_token ?? null;
}

export function cerrarSesion() {
  if (typeof window === "undefined") return;
  try {
    localStorage.removeItem(CLAVE_SESION);
  } catch {
    // no crítico
  }
}

/**
 * Wrapper de fetch que:
 *   1. adjunta "Authorization: Bearer <token>" si hay sesión,
 *   2. si la API responde 401 (token inválido/caducado), limpia la sesión
 *      y redirige a /login — así ningún componente tiene que repetir esa
 *      lógica de error en cada llamada.
 */
export async function fetchAutenticado(url, opciones = {}) {
  const token = obtenerToken();
  const cabeceras = {
    ...(opciones.headers || {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  const respuesta = await fetch(url, { ...opciones, headers: cabeceras });

  if (respuesta.status === 401) {
    cerrarSesion();
    if (typeof window !== "undefined") {
      window.location.href = "/login?motivo=sesion_caducada";
    }
  }

  return respuesta;
}

/**
 * Hook para páginas protegidas: si no hay sesión, redirige a /login.
 * Devuelve { comprobando, sesion }: mientras comprobando es true, no se
 * debe renderizar contenido protegido (evita un parpadeo del contenido
 * antes de redirigir a quien no tiene sesión).
 *
 * Se re-comprueba en cada cambio de ruta (dependencia `router`), porque el
 * layout (y por tanto los componentes que usan este hook) no se remonta al
 * navegar entre páginas del mismo layout: sin esto, tras iniciar sesión y
 * redirigir, el estado podría quedarse desactualizado.
 */
export function useRequerirSesion() {
  const router = useRouter();
  const [estado, setEstado] = useState({ comprobando: true, sesion: null });

  useEffect(() => {
    const sesion = obtenerSesion();
    if (!sesion) {
      router.replace("/login");
      return;
    }
    setEstado({ comprobando: false, sesion });
  }, [router]);

  return estado;
}
