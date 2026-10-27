"use client";

import { useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { apiJson } from "@/lib/api";

/** Shared phase-2 shell: header + Lock + node-model sidebar.
 *
 * Sidebar (corrected spec): Dashboard, Graph, History, Perbandingan,
 * Benchmark (Segera hadir). There is deliberately NO Koneksi menu:
 * provider settings live inside Model nodes.
 */
const LINKS = [
  { label: "Dashboard", href: "/" },
  { label: "Graph", href: "/graph" },
  { label: "History", href: "/history" },
  { label: "Perbandingan", href: "/perbandingan" },
  { label: "Benchmark", href: "", disabled: true },
];

export default function Shell({ title, children }: { title: string; children: ReactNode }) {
  const router = useRouter();

  async function onLock() {
    try {
      const csrf = await apiJson("/api/auth/csrf");
      if (csrf.ok) {
        const { csrf_token } = await csrf.json();
        await apiJson("/api/auth/logout", {
          method: "POST",
          headers: { "X-CSRF-Token": csrf_token },
        });
      }
    } finally {
      router.replace("/gate");
      router.refresh();
    }
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <header
        style={{
          display: "flex", justifyContent: "space-between", alignItems: "center",
          padding: "12px 20px", borderBottom: "1px solid var(--border)", background: "var(--surface)",
        }}
      >
        <strong style={{ fontSize: 18 }}>Harlearn <span className="muted" style={{ fontWeight: 400 }}>· Lab AI</span></strong>
        <button className="btn-ghost" type="button" onClick={onLock}>Lock</button>
      </header>
      <div style={{ display: "flex", flex: 1, minHeight: 0 }}>
        <aside
          style={{
            width: 200, flexShrink: 0, padding: 16, borderRight: "1px solid var(--border)",
            display: "flex", flexDirection: "column", gap: 4,
          }}
        >
          {LINKS.map((link) => (
            <button
              key={link.label}
              type="button"
              disabled={link.disabled}
              className="btn-ghost"
              style={{ textAlign: "left", display: "flex", justifyContent: "space-between", alignItems: "center" }}
              onClick={() => link.href && router.push(link.href)}
            >
              <span>{link.label}</span>
              {link.disabled && <span className="coming-soon">Segera hadir</span>}
            </button>
          ))}
        </aside>
        <main style={{ flex: 1, padding: 24, minWidth: 0 }}>
          <h1 style={{ marginTop: 0 }}>{title}</h1>
          {children}
        </main>
      </div>
    </div>
  );
}
