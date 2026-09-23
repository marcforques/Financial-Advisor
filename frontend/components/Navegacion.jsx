"use client";

/**
 * Navegacion — barra superior con las dos secciones de la app.
 *
 * Usa el enrutado de Next.js (Link) para moverse entre "Crear" (/) y
 * "Mis carteras" (/carteras) sin recargar la página. Resalta la sección
 * activa según la ruta actual.
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { obtenerSesion, cerrarSesion } from "@/lib/auth";

export default function Navegacion() {
  const ruta = usePathname();
  const router = useRouter();
  const [sesion, setSesion] = useState(null);

  // Se re-lee en cada cambio de ruta: el layout no se remonta al navegar,
  // así que sin esto el estado de sesión se quedaría desactualizado justo
  // después de iniciar sesión o cerrarla (que redirigen con router.push).
  useEffect(() => {
    setSesion(obtenerSesion());
  }, [ruta]);

  const salir = () => {
    cerrarSesion();
    setSesion(null);
    router.push("/login");
  };

  const enlaces = [
    { href: "/", etiqueta: "Crear cartera" },
    { href: "/carteras", etiqueta: "Mis carteras" },
  ];

  return (
    <nav style={s.barra}>
      <div style={s.contenido}>
        <div style={s.grupoIzquierda}>
          <div style={s.marca}>Asesor de inversión</div>
          <div style={s.enlaces}>
            {enlaces.map((e) => {
              const activo = ruta === e.href;
              return (
                <Link
                  key={e.href}
                  href={e.href}
                  style={{ ...s.enlace, ...(activo ? s.enlaceActivo : {}) }}
                >
                  {e.etiqueta}
                </Link>
              );
            })}
          </div>
        </div>
        <div style={s.cuenta}>
          {sesion ? (
            <>
              <span style={s.email}>{sesion.usuario?.email}</span>
              <button onClick={salir} style={s.botonSalir}>Cerrar sesión</button>
            </>
          ) : (
            <>
              <Link href="/login" style={s.enlaceCuenta}>Iniciar sesión</Link>
              <Link href="/registro" style={s.enlaceCuentaDestacado}>Crear cuenta</Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}

const TINTA = "#1a2b4a";
const GRIS_SUAVE = "#6b7280";
const GRIS_BORDE = "#e2e5ea";
const BLANCO = "#ffffff";

const s = {
  barra: {
    background: BLANCO,
    borderBottom: `1px solid ${GRIS_BORDE}`,
    position: "sticky",
    top: 0,
    zIndex: 10,
  },
  contenido: {
    maxWidth: 960,
    margin: "0 auto",
    padding: "0 24px",
    height: 60,
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
  },
  grupoIzquierda: {
    display: "flex",
    alignItems: "center",
    gap: 28,
  },
  marca: {
    fontSize: 15,
    fontWeight: 700,
    color: TINTA,
    letterSpacing: "-0.01em",
  },
  enlaces: {
    display: "flex",
    gap: 4,
  },
  enlace: {
    padding: "8px 16px",
    borderRadius: 8,
    fontSize: 14,
    fontWeight: 500,
    color: GRIS_SUAVE,
    transition: "all 0.15s ease",
  },
  enlaceActivo: {
    color: TINTA,
    background: "#f5f8fd",
    fontWeight: 600,
  },
  cuenta: {
    display: "flex",
    alignItems: "center",
    gap: 14,
  },
  email: {
    fontSize: 13.5,
    color: GRIS_SUAVE,
  },
  botonSalir: {
    padding: "7px 14px",
    borderRadius: 8,
    border: `1px solid ${GRIS_BORDE}`,
    background: BLANCO,
    color: GRIS_SUAVE,
    fontSize: 13.5,
    fontWeight: 500,
    cursor: "pointer",
    fontFamily: "inherit",
  },
  enlaceCuenta: {
    fontSize: 13.5,
    fontWeight: 500,
    color: GRIS_SUAVE,
  },
  enlaceCuentaDestacado: {
    padding: "7px 14px",
    borderRadius: 8,
    background: TINTA,
    color: BLANCO,
    fontSize: 13.5,
    fontWeight: 600,
  },
};
