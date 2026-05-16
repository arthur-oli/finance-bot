import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";
import { Sidebar } from "@/components/Sidebar";

export const metadata: Metadata = {
  title: "Finance Bot",
  description: "Controle financeiro pessoal",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body className="bg-gray-950 text-gray-100 min-h-screen flex">
        <Providers>
          <Sidebar />
          <main className="flex-1 px-4 pt-4 pb-24 sm:p-6 overflow-auto">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
