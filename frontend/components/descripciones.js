/**
 * descripciones.js — traduce tickers técnicos a nombres comprensibles.
 *
 * El usuario final no maneja jerga bursátil: "VNQ" no le dice nada, pero
 * "Inmobiliario EEUU (REITs)" sí. Este mapa espeja los metadatos del
 * catálogo del backend para mostrar descripciones legibles en la interfaz.
 *
 * NOTA: es un espejo manual del catálogo del backend. Si el catálogo
 * cambia, actualizar aquí. (Mejora futura: exponer las descripciones desde
 * la API para tener una única fuente de verdad.)
 */

const DESCRIPCIONES = {
  // Renta variable amplia
  SPY: { nombre: "Grandes empresas EEUU (S&P 500)", region: "EEUU" },
  QQQ: { nombre: "Tecnológicas EEUU (Nasdaq 100)", region: "EEUU" },
  VTV: { nombre: "Empresas valor EEUU", region: "EEUU" },
  IWM: { nombre: "Pequeñas empresas EEUU", region: "EEUU" },
  URTH: { nombre: "Acciones globales (MSCI World)", region: "Global" },
  VEA: { nombre: "Mercados desarrollados", region: "Global" },
  IEUR: { nombre: "Acciones Europa", region: "Europa" },
  EZU: { nombre: "Acciones zona euro", region: "Europa" },
  EEM: { nombre: "Mercados emergentes", region: "Emergentes" },
  VWO: { nombre: "Mercados emergentes (Vanguard)", region: "Emergentes" },
  EWJ: { nombre: "Acciones Japón", region: "Asia-Pacífico" },
  AAXJ: { nombre: "Asia sin Japón", region: "Asia-Pacífico" },

  // Sectoriales
  XLK: { nombre: "Sector tecnología EEUU", region: "EEUU" },
  XLV: { nombre: "Sector salud EEUU", region: "EEUU" },
  XLE: { nombre: "Sector energía EEUU", region: "EEUU" },
  XLF: { nombre: "Sector financiero EEUU", region: "EEUU" },
  VNQ: { nombre: "Inmobiliario EEUU (REITs)", region: "EEUU" },

  // Bonos
  AGG: { nombre: "Bonos agregados EEUU", region: "EEUU" },
  TLT: { nombre: "Bonos Tesoro EEUU largo plazo", region: "EEUU" },
  IEF: { nombre: "Bonos Tesoro EEUU medio plazo", region: "EEUU" },
  LQD: { nombre: "Bonos corporativos EEUU", region: "EEUU" },
  TIP: { nombre: "Bonos ligados a inflación EEUU", region: "EEUU" },
  "IEAG.AS": { nombre: "Bonos agregados Europa", region: "Europa" },
  "IEGA.AS": { nombre: "Bonos gobierno Europa", region: "Europa" },
  "IBCI.DE": { nombre: "Bonos ligados a inflación Europa", region: "Europa" },
  BNDX: { nombre: "Bonos internacionales", region: "Global" },
  EMB: { nombre: "Bonos mercados emergentes", region: "Emergentes" },

  // Materias primas
  GLD: { nombre: "Oro", region: "Refugio" },
  SLV: { nombre: "Plata", region: "Refugio" },
  DBC: { nombre: "Cesta de materias primas", region: "Refugio" },
};

/**
 * Devuelve la descripción legible de un ticker.
 * Si el ticker no está en el mapa, devuelve el propio ticker como nombre.
 */
export function metadatosTicker(ticker) {
  return DESCRIPCIONES[ticker] || { nombre: ticker, region: "" };
}