/** @type {import('next').NextConfig} */
const nextConfig = {
  // Genera un servidor autocontenido, apropiado para una imagen Docker
  // pequeña y sin las dependencias de desarrollo.
  output: "standalone",
  turbopack: {
    root: process.cwd(),
  },
};

export default nextConfig;
