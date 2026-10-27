import type { ReactNode } from "react";
import "./globals.css";

export const metadata = {
  title: "Harlearn · Lab AI",
  description: "Harlearn — AI lab (slice 1: gate + dashboard).",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="id">
      <body>{children}</body>
    </html>
  );
}
