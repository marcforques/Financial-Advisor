"use client";

/**
 * Mis carteras — pantalla de gestión de carteras guardadas.
 *
 * FLUJO:
 *   1. Lista las carteras del usuario (GET /carteras/{usuario_id}).
 *   2. Al abrir una, muestra su detalle (posiciones, pesos).
 *   3. Permite rebalancear con las dos modalidades:
 *        - "rebalancear": volver al plan objetivo original.
 *        - "reoptimizar": recalcular el óptimo de hoy.
 *      (POST /carteras/{id}/rebalancear)
 *
 * Usuario temporal fijo ("usuario_local") hasta que exista autenticación.
 */

import { useState, useEffect } from "react";
import { metadatosTicker } from "@/components/descripciones";
import { fetchAutenticado, useRequerirSesion } from "@/lib/auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function MisCarteras() {
  // Página protegida: sin sesión, redirige a /login.
  const { comprobando, sesion } = useRequerirSesion();

  const [carteras, setCarteras] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [seleccionada, setSeleccionada] = useState(null);
  const [error, setError] = useState("");

  // Cargar la lista de carteras al entrar, en cuanto hay sesión confirmada.
  useEffect(() => {
    if (sesion) cargarCarteras();
  }, [sesion]);

  const cargarCarteras = async () => {
    setCargando(true);
    setError("");
    try {
      // Ya no se pasa el usuario por la URL: el backend identifica al
      // usuario a partir del token de la cabecera Authorization.
      const res = await fetchAutenticado(`${API_URL}/carteras`);
      if (!res.ok) throw new Error("No se pudieron cargar las carteras.");
      const datos = await res.json();
      setCarteras(datos);
    } catch (e) {
      setError("No se pudieron cargar tus carteras. ¿Está el servidor en marcha?");
    } finally {
      setCargando(false);
    }
  };

  if (comprobando || !sesion) {
    return <div style={s.pagina}><div style={s.aviso}>Comprobando sesión…</div></div>;
  }

  // Si hay una cartera seleccionada, mostramos su detalle.
  if (seleccionada) {
    return (
      <DetalleCartera
        cartera={seleccionada}
        onVolver={() => setSeleccionada(null)}
      />
    );
  }

  return (
    <div style={s.pagina}>
      <div style={s.contenedor}>
        <h1 style={s.titulo}>Mis carteras</h1>
        <p style={s.subtitulo}>
          Aquí están las carteras que has creado. Ábrelas para ver el detalle o
          analizar si conviene rebalancear.
        </p>

        {cargando && <div style={s.aviso}>Cargando tus carteras…</div>}
        {error && <div style={s.errorCaja}>{error}</div>}

        {!cargando && !error && carteras.length === 0 && (
          <div style={s.vacio}>
            <p style={s.vacioTexto}>Aún no tienes carteras guardadas.</p>
            <a href="/" style={s.vacioEnlace}>Crear mi primera cartera</a>
          </div>
        )}

        <div style={s.lista}>
          {carteras.map((c) => (
            <button key={c.id} style={s.tarjeta} onClick={() => setSeleccionada(c)}>
              <div style={s.tarjetaInfo}>
                <span style={s.tarjetaNombre}>{c.nombre}</span>
                <span style={s.tarjetaMeta}>
                  {c.posiciones.length} posiciones · {c.nivel_riesgo}
                  {c.es_externa ? " · externa" : ""}
                </span>
              </div>
              <span style={s.tarjetaFlecha}>→</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Detalle de una cartera + rebalanceo ───

function DetalleCartera({ cartera, onVolver }) {
  const [recomendacion, setRecomendacion] = useState(null);
  const [analizando, setAnalizando] = useState(false);
  const [error, setError] = useState("");

  // Precios actuales simulados: en un sistema real vendrían de mercado.
  // Aquí usamos los precios de compra como aproximación para la demo,
  // salvo que el backend los provea. (El backend recalcula con datos reales.)
  const rebalancear = async (modo) => {
    setAnalizando(true);
    setError("");
    setRecomendacion(null);
    try {
      const tickers = cartera.posiciones.map((p) => p.ticker).join(",");
      const resPrecios = await fetchAutenticado(
        `${API_URL}/carteras/precios-actuales?tickers=${tickers}`
      );
      if (!resPrecios.ok) {
        throw new Error("No se pudieron obtener los precios de mercado actuales.");
      }
      const precios_actuales = await resPrecios.json();

      const res = await fetchAutenticado(`${API_URL}/carteras/${cartera.id}/rebalancear`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          modo,
          precios_actuales,
          capital: cartera.posiciones.reduce(
            (sum, p) => sum + p.participaciones * p.precio_compra, 0
          ),
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "No se pudo analizar el rebalanceo.");
      }
      const datos = await res.json();
      setRecomendacion(datos);
    } catch (e) {
      setError(e.message);
    } finally {
      setAnalizando(false);
    }
  };

  const capital = cartera.posiciones.reduce(
    (sum, p) => sum + p.participaciones * p.precio_compra, 0
  );

  return (
    <div style={s.pagina}>
      <div style={s.contenedor}>
        <button onClick={onVolver} style={s.volver}>← Volver a mis carteras</button>

        <h1 style={s.titulo}>{cartera.nombre}</h1>
        <p style={s.subtitulo}>
          {cartera.nivel_riesgo} · horizonte {cartera.horizonte_anios} años ·
          {" "}capital invertido {capital.toLocaleString("es-ES", { maximumFractionDigits: 0 })}€
        </p>

        {/* Posiciones */}
        <h2 style={s.seccionTitulo}>Posiciones</h2>
        <div style={s.posiciones}>
          {cartera.posiciones.map((p) => {
            const meta = metadatosTicker(p.ticker);
            const valor = p.participaciones * p.precio_compra;
            const peso = valor / capital;
            return (
              <div key={p.ticker} style={s.filaPos}>
                <div style={s.posInfo}>
                  <span style={s.posTicker}>{p.ticker}</span>
                  <span style={s.posNombre}>{meta.nombre}</span>
                </div>
                <div style={s.posBarraFondo}>
                  <div style={{ ...s.posBarra, width: `${peso * 100}%` }} />
                </div>
                <span style={s.posPeso}>{(peso * 100).toFixed(1)}%</span>
              </div>
            );
          })}
        </div>

        {/* Explicación (si la cartera la generó el sistema; las externas no la tienen) */}
        {cartera.explicacion && (
          <>
            <h2 style={s.seccionTitulo}>Por qué esta cartera</h2>
            <div style={s.explicacion}>
              {cartera.explicacion.split("\n").filter(Boolean).map((parrafo, i) => (
                <p key={i} style={s.parrafo}>{parrafo.replace(/[#*]/g, "")}</p>
              ))}
            </div>
          </>
        )}

        {/* Rebalanceo */}
        <h2 style={s.seccionTitulo}>Rebalancear</h2>
        <p style={s.rebalanceoIntro}>
          Analiza si conviene ajustar tu cartera. Puedes volver a tu plan
          original o recalcular la cartera óptima de hoy.
        </p>
        <div style={s.botonesRebalanceo}>
          <button
            style={s.botonModo}
            onClick={() => rebalancear("rebalancear")}
            disabled={analizando || cartera.es_externa}
          >
            Volver al plan original
          </button>
          <button
            style={s.botonModo}
            onClick={() => rebalancear("reoptimizar")}
            disabled={analizando}
          >
            Recalcular óptimo de hoy
          </button>
        </div>
        {cartera.es_externa && (
          <p style={s.notaExterna}>
            Esta cartera es externa (la introdujiste tú), así que solo puede
            reoptimizarse: no tiene un plan original guardado.
          </p>
        )}

        {analizando && <div style={s.aviso}>Analizando…</div>}
        {error && <div style={s.errorCaja}>{error}</div>}

        {recomendacion && <ResultadoRebalanceo rec={recomendacion} />}
      </div>
    </div>
  );
}

function ResultadoRebalanceo({ rec }) {
  return (
    <div style={s.recuadro}>
      <div style={{ ...s.veredicto, color: rec.rebalancear ? "#0a7d3f" : "#6b7280" }}>
        {rec.rebalancear ? "Conviene rebalancear" : "No conviene rebalancear ahora"}
      </div>
      <p style={s.motivo}>{rec.motivo}</p>

      {rec.rebalancear && rec.plan && rec.plan.length > 0 && (
        <>
          <div style={s.planTitulo}>Plan de operaciones</div>
          {rec.plan.map((op, i) => (
            <div key={i} style={s.opFila}>
              <span style={{
                ...s.opAccion,
                color: op.accion === "VENDER" ? "#b42318" : "#0a7d3f",
              }}>
                {op.accion}
              </span>
              <span style={s.opDetalle}>
                {op.importe.toLocaleString("es-ES", { maximumFractionDigits: 2 })}€ de {op.activo}
              </span>
            </div>
          ))}
          <div style={s.costes}>
            <span>Coste transacción: {rec.coste_transaccion?.toFixed(2)}€</span>
            <span>Impuesto: {rec.impuesto?.toFixed(2)}€</span>
            <span style={s.costeTotal}>Total: {rec.coste_total?.toFixed(2)}€</span>
          </div>
        </>
      )}
    </div>
  );
}

// ─── Estilos ───
const TINTA = "#1a2b4a";
const GRIS_TEXTO = "#3a3f4a";
const GRIS_SUAVE = "#6b7280";
const GRIS_BORDE = "#e2e5ea";
const FONDO = "#fbfcfd";
const BLANCO = "#ffffff";

const s = {
  pagina: { minHeight: "calc(100vh - 60px)", background: FONDO, padding: "40px 20px" },
  contenedor: { maxWidth: 640, margin: "0 auto" },
  titulo: { fontSize: 28, fontWeight: 700, color: TINTA, margin: "0 0 8px", letterSpacing: "-0.02em" },
  subtitulo: { fontSize: 15, color: GRIS_SUAVE, margin: "0 0 32px", lineHeight: 1.55 },
  aviso: { padding: "16px", color: GRIS_SUAVE, fontSize: 15 },
  errorCaja: { padding: "14px 16px", background: "#fef3f2", border: "1px solid #fecdca", borderRadius: 10, color: "#b42318", fontSize: 14, marginTop: 16 },
  vacio: { textAlign: "center", padding: "48px 20px", background: BLANCO, borderRadius: 14, border: `1px solid ${GRIS_BORDE}` },
  vacioTexto: { fontSize: 15, color: GRIS_SUAVE, margin: "0 0 16px" },
  vacioEnlace: { fontSize: 15, fontWeight: 600, color: TINTA, textDecoration: "underline" },
  lista: { display: "flex", flexDirection: "column", gap: 12 },
  tarjeta: { display: "flex", alignItems: "center", justifyContent: "space-between", padding: "20px 22px", borderRadius: 12, border: `1px solid ${GRIS_BORDE}`, background: BLANCO, cursor: "pointer", width: "100%", fontFamily: "inherit", transition: "all 0.15s ease", textAlign: "left" },
  tarjetaInfo: { display: "flex", flexDirection: "column", gap: 4 },
  tarjetaNombre: { fontSize: 16, fontWeight: 600, color: GRIS_TEXTO },
  tarjetaMeta: { fontSize: 13.5, color: GRIS_SUAVE },
  tarjetaFlecha: { fontSize: 18, color: GRIS_SUAVE },
  volver: { border: "none", background: "none", color: TINTA, fontSize: 14, fontWeight: 500, cursor: "pointer", fontFamily: "inherit", padding: 0, marginBottom: 24 },
  seccionTitulo: { fontSize: 13, fontWeight: 600, color: GRIS_SUAVE, textTransform: "uppercase", letterSpacing: "0.05em", margin: "32px 0 16px" },
  posiciones: { display: "flex", flexDirection: "column", gap: 14 },
  filaPos: { display: "flex", alignItems: "center", gap: 14 },
  posInfo: { display: "flex", flexDirection: "column", width: 150, flexShrink: 0 },
  posTicker: { fontSize: 15, fontWeight: 600, color: GRIS_TEXTO },
  posNombre: { fontSize: 12.5, color: GRIS_SUAVE, lineHeight: 1.3 },
  posBarraFondo: { flex: 1, height: 8, background: GRIS_BORDE, borderRadius: 99, overflow: "hidden" },
  posBarra: { height: "100%", background: TINTA, borderRadius: 99 },
  posPeso: { fontSize: 14, fontWeight: 600, color: TINTA, width: 52, textAlign: "right", fontVariantNumeric: "tabular-nums" },
  explicacion: { background: "#f8fafc", border: `1px solid ${GRIS_BORDE}`, borderRadius: 12, padding: "24px 28px", marginBottom: 8 },
  parrafo: { fontSize: 14.5, color: GRIS_TEXTO, lineHeight: 1.6, margin: "0 0 12px" },
  rebalanceoIntro: { fontSize: 14.5, color: GRIS_SUAVE, lineHeight: 1.55, margin: "0 0 20px" },
  botonesRebalanceo: { display: "flex", gap: 12 },
  botonModo: { flex: 1, padding: "14px 18px", borderRadius: 10, border: `1.5px solid ${TINTA}`, background: BLANCO, color: TINTA, fontSize: 14.5, fontWeight: 600, cursor: "pointer", fontFamily: "inherit", transition: "all 0.15s ease" },
  notaExterna: { fontSize: 13, color: GRIS_SUAVE, fontStyle: "italic", marginTop: 12, lineHeight: 1.5 },
  recuadro: { marginTop: 24, padding: "24px", borderRadius: 14, border: `1px solid ${GRIS_BORDE}`, background: BLANCO },
  veredicto: { fontSize: 17, fontWeight: 700, marginBottom: 8 },
  motivo: { fontSize: 14.5, color: GRIS_TEXTO, lineHeight: 1.6, margin: "0 0 20px" },
  planTitulo: { fontSize: 13, fontWeight: 600, color: GRIS_SUAVE, textTransform: "uppercase", letterSpacing: "0.05em", margin: "0 0 12px" },
  opFila: { display: "flex", gap: 12, padding: "8px 0", alignItems: "center" },
  opAccion: { fontSize: 13, fontWeight: 700, width: 64, letterSpacing: "0.03em" },
  opDetalle: { fontSize: 14.5, color: GRIS_TEXTO },
  costes: { display: "flex", gap: 20, marginTop: 16, paddingTop: 16, borderTop: `1px solid ${GRIS_BORDE}`, fontSize: 13.5, color: GRIS_SUAVE, flexWrap: "wrap" },
  costeTotal: { fontWeight: 600, color: TINTA },
};