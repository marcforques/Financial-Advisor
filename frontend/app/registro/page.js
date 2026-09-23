"use client";

/**
 * /registro — alta de cuenta nueva.
 *
 * Llama a POST {API_URL}/auth/registro. Con la confirmación por email
 * desactivada en Supabase (auto-confirm), el backend devuelve una sesión
 * ya utilizable en la misma respuesta, así que tras registrarse el usuario
 * entra directamente, sin paso intermedio de "revisa tu correo".
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { guardarSesion } from "@/lib/auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function Registro() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmar, setConfirmar] = useState("");
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState("");

  const enviar = async (e) => {
    e.preventDefault();
    setError("");

    if (password.length < 8) {
      setError("La contraseña debe tener al menos 8 caracteres.");
      return;
    }
    if (password !== confirmar) {
      setError("Las contraseñas no coinciden.");
      return;
    }

    setCargando(true);
    try {
      const respuesta = await fetch(`${API_URL}/auth/registro`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const datos = await respuesta.json();
      if (!respuesta.ok) {
        throw new Error(datos.detail || "No se pudo crear la cuenta.");
      }
      guardarSesion(datos);
      router.push("/");
    } catch (e) {
      setError(e.message);
    } finally {
      setCargando(false);
    }
  };

  return (
    <div style={s.pagina}>
      <form onSubmit={enviar} style={s.marco}>
        <div style={s.marca}>Asesor de inversión</div>
        <h1 style={s.titulo}>Crea tu cuenta</h1>
        <p style={s.subtitulo}>Regístrate para guardar y gestionar tus carteras.</p>

        <label style={s.etiqueta}>
          Email
          <input
            type="email" required autoFocus
            value={email} onChange={(e) => setEmail(e.target.value)}
            style={s.input} placeholder="tucorreo@ejemplo.com"
          />
        </label>

        <label style={s.etiqueta}>
          Contraseña
          <input
            type="password" required minLength={8}
            value={password} onChange={(e) => setPassword(e.target.value)}
            style={s.input} placeholder="Mínimo 8 caracteres"
          />
        </label>

        <label style={s.etiqueta}>
          Confirmar contraseña
          <input
            type="password" required
            value={confirmar} onChange={(e) => setConfirmar(e.target.value)}
            style={s.input} placeholder="••••••••"
          />
        </label>

        {error && <div style={s.error}>{error}</div>}

        <button type="submit" style={s.boton} disabled={cargando}>
          {cargando ? "Creando cuenta…" : "Crear cuenta"}
        </button>

        <p style={s.pie}>
          ¿Ya tienes cuenta? <Link href="/login" style={s.enlace}>Inicia sesión</Link>
        </p>
      </form>
    </div>
  );
}

const TINTA = "#1a2b4a";
const GRIS_TEXTO = "#3a3f4a";
const GRIS_SUAVE = "#6b7280";
const GRIS_BORDE = "#e2e5ea";
const FONDO = "#fbfcfd";
const BLANCO = "#ffffff";

const s = {
  pagina: { minHeight: "calc(100vh - 60px)", background: FONDO, display: "flex", alignItems: "center", justifyContent: "center", padding: "40px 20px" },
  marco: { width: "100%", maxWidth: 400, background: BLANCO, borderRadius: 16, border: `1px solid ${GRIS_BORDE}`, padding: "36px 36px 32px", boxShadow: "0 1px 3px rgba(16,24,40,0.04)", display: "flex", flexDirection: "column" },
  marca: { fontSize: 13, fontWeight: 600, color: TINTA, letterSpacing: "-0.01em", marginBottom: 20 },
  titulo: { fontSize: 24, fontWeight: 600, color: TINTA, margin: "0 0 6px", letterSpacing: "-0.02em" },
  subtitulo: { fontSize: 14.5, color: GRIS_SUAVE, margin: "0 0 24px", lineHeight: 1.5 },
  etiqueta: { display: "flex", flexDirection: "column", gap: 6, fontSize: 13.5, fontWeight: 600, color: GRIS_TEXTO, marginBottom: 16 },
  input: { padding: "11px 14px", borderRadius: 10, border: `1.5px solid ${GRIS_BORDE}`, fontSize: 15, color: GRIS_TEXTO, fontFamily: "inherit", outline: "none", boxSizing: "border-box" },
  error: { padding: "10px 14px", background: "#fef3f2", border: "1px solid #fecdca", borderRadius: 10, color: "#b42318", fontSize: 13.5, marginBottom: 16 },
  boton: { padding: "13px 20px", borderRadius: 10, border: "none", background: TINTA, color: BLANCO, fontSize: 15, fontWeight: 600, cursor: "pointer", fontFamily: "inherit", marginTop: 4 },
  pie: { fontSize: 13.5, color: GRIS_SUAVE, textAlign: "center", marginTop: 20, marginBottom: 0 },
  enlace: { color: TINTA, fontWeight: 600, textDecoration: "underline" },
};
