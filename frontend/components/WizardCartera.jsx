"use client";

/**
 * WizardCartera — asistente guiado de creación de cartera (5 pasos).
 *
 * Estética: sobria y profesional (fintech serio). Un paso por pantalla,
 * progreso visible, mucho aire. Al terminar, llama a la API (POST /cartera)
 * y muestra el resultado con su explicación.
 *
 * PUNTOS DE CONEXIÓN CON TU BACKEND:
 *   - Envía a POST {API_URL}/cartera un JSON con:
 *       nivel_riesgo, horizonte_anios, capital, objetivo, texto_libre
 *   - Recibe la RespuestaCartera: activos[], métricas, explicacion.
 *
 * Los valores de nivel_riesgo y objetivo deben coincidir EXACTAMENTE con
 * los enums del backend (NivelRiesgo, ObjetivoInversion).
 */

import { useState } from "react";
import { fetchAutenticado, useRequerirSesion } from "@/lib/auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

// ─── Opciones (deben coincidir con los enums del backend) ───
const OBJETIVOS = [
  { valor: "jubilacion", titulo: "Jubilación", descripcion: "Construir un patrimonio para el largo plazo." },
  { valor: "crecimiento", titulo: "Crecimiento", descripcion: "Hacer crecer mi capital de forma sostenida." },
  { valor: "preservar_capital", titulo: "Preservar capital", descripcion: "Proteger lo que tengo con riesgo bajo." },
];

const PERFILES_RIESGO = [
  { valor: "conservador", titulo: "Conservador", descripcion: "Prefiero estabilidad. Las caídas me quitan el sueño." },
  { valor: "moderado", titulo: "Moderado", descripcion: "Acepto algo de vaivén a cambio de más rentabilidad." },
  { valor: "agresivo", titulo: "Agresivo", descripcion: "Busco máximo crecimiento y tolero las caídas." },
];

const TOTAL_PASOS = 5;

export default function WizardCartera() {
  // Página protegida: sin sesión, redirige a /login. Mientras se comprueba,
  // no renderizamos el asistente (evita un parpadeo de contenido protegido).
  const { comprobando, sesion } = useRequerirSesion();

  const [paso, setPaso] = useState(1);
  const [datos, setDatos] = useState({
    capital: "",
    horizonte_anios: "",
    objetivo: "",
    nivel_riesgo: "",
    texto_libre: "",
  });
  const [cargando, setCargando] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [error, setError] = useState("");

  const actualizar = (campo, valor) => {
    setDatos((d) => ({ ...d, [campo]: valor }));
    setError("");
  };

  // Validación por paso: no avanzar sin el dato necesario.
  const pasoValido = () => {
    switch (paso) {
      case 1: return Number(datos.capital) > 0;
      case 2: return Number(datos.horizonte_anios) >= 1;
      case 3: return datos.objetivo !== "";
      case 4: return datos.nivel_riesgo !== "";
      case 5: return true; // el texto libre es opcional
      default: return false;
    }
  };

  const siguiente = () => {
    if (!pasoValido()) {
      setError("Completa este paso para continuar.");
      return;
    }
    if (paso < TOTAL_PASOS) setPaso(paso + 1);
    else enviar();
  };

  const atras = () => {
    setError("");
    if (paso > 1) setPaso(paso - 1);
  };

  // Llamada a la API: construye la cartera.
  const enviar = async () => {
    setCargando(true);
    setError("");
    try {
      const respuesta = await fetchAutenticado(`${API_URL}/cartera`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nivel_riesgo: datos.nivel_riesgo,
          horizonte_anios: Number(datos.horizonte_anios),
          capital: Number(datos.capital),
          objetivo: datos.objetivo,
          texto_libre: datos.texto_libre,
        }),
      });
      if (!respuesta.ok) throw new Error("No se pudo generar la cartera.");
      const cartera = await respuesta.json();
      setResultado(cartera);
    } catch (e) {
      setError("Hubo un problema al generar tu cartera. Inténtalo de nuevo.");
    } finally {
      setCargando(false);
    }
  };

  const reiniciar = () => {
    setPaso(1);
    setDatos({ capital: "", horizonte_anios: "", objetivo: "", nivel_riesgo: "", texto_libre: "" });
    setResultado(null);
    setError("");
  };

  // Mientras se comprueba la sesión (o si no hay, antes de que el hook
  // redirija) no mostramos el asistente.
  if (comprobando || !sesion) {
    return <div style={s.pagina}><div style={s.marco}>Comprobando sesión…</div></div>;
  }

  // Si hay resultado, mostramos la pantalla de cartera.
  if (resultado) {
    return <ResultadoCartera resultado={resultado} datos={datos} onReiniciar={reiniciar} />;
  }

  return (
    <div style={s.pagina}>
      <div style={s.marco}>
        {/* Cabecera con progreso */}
        <div style={s.cabecera}>
          <div style={s.marca}>Asesor de inversión</div>
          <div style={s.pasoTexto}>Paso {paso} de {TOTAL_PASOS}</div>
        </div>
        <div style={s.barraFondo}>
          <div style={{ ...s.barraProgreso, width: `${(paso / TOTAL_PASOS) * 100}%` }} />
        </div>

        {/* Contenido del paso */}
        <div style={s.contenido}>
          {paso === 1 && (
            <Paso titulo="¿Cuánto quieres invertir?" subtitulo="El capital con el que quieres empezar tu cartera.">
              <div style={s.campoMoneda}>
                <span style={s.simboloMoneda}>€</span>
                <input
                  type="number" inputMode="numeric" min="0" placeholder="10.000"
                  value={datos.capital}
                  onChange={(e) => actualizar("capital", e.target.value)}
                  style={s.inputGrande} autoFocus
                />
              </div>
            </Paso>
          )}

          {paso === 2 && (
            <Paso titulo="¿Durante cuánto tiempo?" subtitulo="Tu horizonte de inversión en años. Cuanto más largo, más riesgo puedes asumir.">
              <div style={s.campoMoneda}>
                <input
                  type="number" inputMode="numeric" min="1" max="50" placeholder="20"
                  value={datos.horizonte_anios}
                  onChange={(e) => actualizar("horizonte_anios", e.target.value)}
                  style={s.inputGrande} autoFocus
                />
                <span style={s.sufijo}>años</span>
              </div>
            </Paso>
          )}

          {paso === 3 && (
            <Paso titulo="¿Cuál es tu meta?" subtitulo="Elige el objetivo que mejor describe lo que buscas.">
              <div style={s.opciones}>
                {OBJETIVOS.map((o) => (
                  <Tarjeta key={o.valor} seleccionada={datos.objetivo === o.valor}
                    onClick={() => actualizar("objetivo", o.valor)}
                    titulo={o.titulo} descripcion={o.descripcion} />
                ))}
              </div>
            </Paso>
          )}

          {paso === 4 && (
            <Paso titulo="¿Cómo te sientes ante las caídas?" subtitulo="Tu tolerancia al riesgo define el equilibrio de tu cartera.">
              <div style={s.opciones}>
                {PERFILES_RIESGO.map((p) => (
                  <Tarjeta key={p.valor} seleccionada={datos.nivel_riesgo === p.valor}
                    onClick={() => actualizar("nivel_riesgo", p.valor)}
                    titulo={p.titulo} descripcion={p.descripcion} />
                ))}
              </div>
            </Paso>
          )}

          {paso === 5 && (
            <Paso titulo="¿Algo más que debamos saber?" subtitulo="Cuéntanos cualquier preocupación o preferencia. Es opcional, pero nos ayuda a afinar (por ejemplo: «me preocupa la inflación»).">
              <textarea
                placeholder="Escribe aquí lo que quieras que tengamos en cuenta…"
                value={datos.texto_libre}
                onChange={(e) => actualizar("texto_libre", e.target.value)}
                style={s.textarea} rows={4} autoFocus
              />
            </Paso>
          )}

          {error && <div style={s.error}>{error}</div>}
        </div>

        {/* Navegación */}
        <div style={s.navegacion}>
          {paso > 1 ? (
            <button onClick={atras} style={s.botonSecundario} disabled={cargando}>Atrás</button>
          ) : <span />}
          <button onClick={siguiente} style={s.botonPrimario} disabled={cargando}>
            {cargando ? "Generando tu cartera…" : paso < TOTAL_PASOS ? "Continuar" : "Ver mi cartera"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Subcomponentes ───

function Paso({ titulo, subtitulo, children }) {
  return (
    <div style={s.paso}>
      <h1 style={s.titulo}>{titulo}</h1>
      <p style={s.subtitulo}>{subtitulo}</p>
      <div style={s.campo}>{children}</div>
    </div>
  );
}

function Tarjeta({ titulo, descripcion, seleccionada, onClick }) {
  return (
    <button onClick={onClick} style={{ ...s.tarjeta, ...(seleccionada ? s.tarjetaSel : {}) }}>
      <span style={{ ...s.tarjetaTitulo, ...(seleccionada ? s.tarjetaTituloSel : {}) }}>{titulo}</span>
      <span style={s.tarjetaDesc}>{descripcion}</span>
    </button>
  );
}

function ResultadoCartera({ resultado, datos, onReiniciar }) {
  const pct = (n) => `${(n * 100).toFixed(1)}%`;
  return (
    <div style={s.pagina}>
      <div style={{ ...s.marco, ...s.marcoResultado }}>
        <div style={s.cabecera}>
          <div style={s.marca}>Tu cartera recomendada</div>
          <button onClick={onReiniciar} style={s.enlace}>Empezar de nuevo</button>
        </div>

        <div style={s.metricas}>
          <Metrica etiqueta="Rentabilidad esperada" valor={pct(resultado.rentabilidad_esperada)} />
          <Metrica etiqueta="Volatilidad" valor={pct(resultado.volatilidad)} />
          <Metrica etiqueta="Ratio de Sharpe" valor={resultado.sharpe.toFixed(2)} />
        </div>

        <div style={s.seccionActivos}>
          <h2 style={s.seccionTitulo}>Distribución</h2>
          {resultado.activos.map((a) => (
            <div key={a.ticker} style={s.filaActivo}>
              <div style={s.activoInfo}>
                <span style={s.activoTicker}>{a.ticker}</span>
                <span style={s.activoRegion}>{a.region}</span>
              </div>
              <div style={s.activoBarraFondo}>
                <div style={{ ...s.activoBarra, width: pct(a.peso) }} />
              </div>
              <span style={s.activoImporte}>
                {a.importe.toLocaleString("es-ES", { maximumFractionDigits: 0 })}€
              </span>
              <span style={s.activoPeso}>{pct(a.peso)}</span>
            </div>
          ))}
        </div>

        <div style={s.seccionExplicacion}>
          <h2 style={s.seccionTitulo}>Por qué esta cartera</h2>
          <div style={s.explicacion}>
            {resultado.explicacion.split("\n").filter(Boolean).map((parrafo, i) => (
              <p key={i} style={s.parrafo}>{parrafo.replace(/[#*]/g, "")}</p>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function Metrica({ etiqueta, valor }) {
  return (
    <div style={s.metrica}>
      <span style={s.metricaValor}>{valor}</span>
      <span style={s.metricaEtiqueta}>{etiqueta}</span>
    </div>
  );
}

// ─── Estilos (sobrio y profesional) ───
const TINTA = "#1a2b4a";      // azul tinta profundo (acento serio)
const TINTA_SUAVE = "#2d4470";
const GRIS_TEXTO = "#3a3f4a";
const GRIS_SUAVE = "#6b7280";
const GRIS_BORDE = "#e2e5ea";
const FONDO = "#fbfcfd";
const BLANCO = "#ffffff";

const s = {
  pagina: { minHeight: "100vh", background: FONDO, display: "flex", alignItems: "flex-start", justifyContent: "center", padding: "48px 20px", fontFamily: "'Inter', system-ui, sans-serif", color: GRIS_TEXTO },
  marco: { width: "100%", maxWidth: 560, background: BLANCO, borderRadius: 16, border: `1px solid ${GRIS_BORDE}`, padding: "36px 40px 32px", boxShadow: "0 1px 3px rgba(16,24,40,0.04)" },
  marcoResultado: { maxWidth: 760 },
  cabecera: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 },
  marca: { fontSize: 14, fontWeight: 600, color: TINTA, letterSpacing: "-0.01em" },
  pasoTexto: { fontSize: 13, color: GRIS_SUAVE, fontVariantNumeric: "tabular-nums" },
  barraFondo: { height: 4, background: GRIS_BORDE, borderRadius: 99, overflow: "hidden", marginBottom: 40 },
  barraProgreso: { height: "100%", background: TINTA, borderRadius: 99, transition: "width 0.4s cubic-bezier(0.4,0,0.2,1)" },
  contenido: { minHeight: 280 },
  paso: {},
  titulo: { fontSize: 26, fontWeight: 600, color: TINTA, margin: "0 0 8px", letterSpacing: "-0.02em", lineHeight: 1.25 },
  subtitulo: { fontSize: 15, color: GRIS_SUAVE, margin: "0 0 32px", lineHeight: 1.55 },
  campo: {},
  campoMoneda: { display: "flex", alignItems: "center", gap: 8, borderBottom: `2px solid ${GRIS_BORDE}`, paddingBottom: 8 },
  simboloMoneda: { fontSize: 32, fontWeight: 500, color: GRIS_SUAVE },
  sufijo: { fontSize: 20, color: GRIS_SUAVE },
  inputGrande: { flex: 1, border: "none", outline: "none", fontSize: 32, fontWeight: 500, color: TINTA, background: "transparent", fontVariantNumeric: "tabular-nums", width: "100%", fontFamily: "inherit" },
  opciones: { display: "flex", flexDirection: "column", gap: 12 },
  tarjeta: { display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 4, padding: "18px 20px", borderRadius: 12, border: `1.5px solid ${GRIS_BORDE}`, background: BLANCO, cursor: "pointer", textAlign: "left", transition: "all 0.15s ease", width: "100%", fontFamily: "inherit" },
  tarjetaSel: { border: `1.5px solid ${TINTA}`, background: "#f5f8fd" },
  tarjetaTitulo: { fontSize: 16, fontWeight: 600, color: GRIS_TEXTO },
  tarjetaTituloSel: { color: TINTA },
  tarjetaDesc: { fontSize: 14, color: GRIS_SUAVE, lineHeight: 1.45 },
  textarea: { width: "100%", padding: "14px 16px", borderRadius: 12, border: `1.5px solid ${GRIS_BORDE}`, fontSize: 15, color: GRIS_TEXTO, fontFamily: "inherit", outline: "none", resize: "vertical", lineHeight: 1.55, boxSizing: "border-box" },
  error: { marginTop: 16, fontSize: 14, color: "#b42318" },
  navegacion: { display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 36 },
  botonPrimario: { padding: "13px 28px", borderRadius: 10, border: "none", background: TINTA, color: BLANCO, fontSize: 15, fontWeight: 600, cursor: "pointer", fontFamily: "inherit", transition: "background 0.15s ease", marginLeft: "auto" },
  botonSecundario: { padding: "13px 24px", borderRadius: 10, border: `1.5px solid ${GRIS_BORDE}`, background: BLANCO, color: GRIS_SUAVE, fontSize: 15, fontWeight: 500, cursor: "pointer", fontFamily: "inherit" },
  enlace: { border: "none", background: "none", color: TINTA, fontSize: 14, fontWeight: 500, cursor: "pointer", fontFamily: "inherit", textDecoration: "underline" },
  // Resultado
  metricas: { display: "flex", gap: 12, marginBottom: 32, marginTop: 8 },
  metrica: { flex: 1, display: "flex", flexDirection: "column", gap: 4, padding: "16px 18px", borderRadius: 12, background: "#f5f8fd", border: `1px solid ${GRIS_BORDE}` },
  metricaValor: { fontSize: 22, fontWeight: 600, color: TINTA, fontVariantNumeric: "tabular-nums" },
  metricaEtiqueta: { fontSize: 12.5, color: GRIS_SUAVE, lineHeight: 1.3 },
  seccionActivos: { marginBottom: 32 },
  seccionTitulo: { fontSize: 13, fontWeight: 600, color: GRIS_SUAVE, textTransform: "uppercase", letterSpacing: "0.05em", margin: "0 0 16px" },
  filaActivo: { display: "flex", alignItems: "center", gap: 14, marginBottom: 14 },
  activoInfo: { display: "flex", flexDirection: "column", width: 90, flexShrink: 0 },
  activoTicker: { fontSize: 15, fontWeight: 600, color: GRIS_TEXTO },
  activoRegion: { fontSize: 12, color: GRIS_SUAVE },
  activoBarraFondo: { flex: 1, height: 8, background: GRIS_BORDE, borderRadius: 99, overflow: "hidden" },
  activoBarra: { height: "100%", background: TINTA, borderRadius: 99 },
  activoImporte: { fontSize: 13.5, color: GRIS_SUAVE, width: 74, textAlign: "right", fontVariantNumeric: "tabular-nums", flexShrink: 0 },
  activoPeso: { fontSize: 14, fontWeight: 600, color: TINTA, width: 52, textAlign: "right", fontVariantNumeric: "tabular-nums" },
  seccionExplicacion: {},
  explicacion: { background: "#f8fafc", border: `1px solid ${GRIS_BORDE}`, borderRadius: 12, padding: "24px 28px" },
  parrafo: { fontSize: 14.5, color: GRIS_TEXTO, lineHeight: 1.6, margin: "0 0 12px" },
};
