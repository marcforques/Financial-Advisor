import { Inter } from "next/font/google";
import "./globals.css";
import Navegacion from "@/components/Navegacion";

const inter = Inter({ subsets: ["latin"] });

export const metadata = {
  title: "Asesor de inversión",
  description: "Asesor financiero inteligente para construir y mantener tu cartera.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="es">
      <body className={inter.className}>
        <Navegacion />
        {children}
      </body>
    </html>
  );
}