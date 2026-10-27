"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiJson } from "@/lib/api";

/**
 * Dashboard, slice 1: header + Lock only. The node canvas, connections,
 * profiles, runs, comparisons, and benchmarks do NOT exist yet — the
 * sidebar below is an honest skeleton, clearly labelled, and its items
 * are disabled rather than pretending to work.
 */
const SIDEBAR = ["Dashboard", "Koneksi", "Profil", "Tugas", "Run", "Perbandingan", "Benchmark"];

export default function DashboardPage() {
  const router = useRouter();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    // The API is the authority: middleware only redirects on a missing
    // cookie name, it cannot validate or check revocation.
    apiJson("/api/auth/me").then((res) => {
      if (!res.ok) router.replace("/gate");
      else setChecked(true);
    }).catch(() => router.replace("/gate"));
  }, [router]);

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

  if (!checked) {
    return <main style={{ padding: 24 }} className="muted">Memeriksa sesi…</main>;
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
          {SIDEBAR.map((item, i) => (
            <button
              key={item}
              type="button"
              disabled={i !== 0}
              className="btn-ghost"
              style={{ textAlign: "left", display: "flex", justifyContent: "space-between", alignItems: "center" }}
              aria-disabled={i !== 0}
            >
              <span>{item}</span>
              {i !== 0 && <span className="coming-soon">Segera hadir</span>}
            </button>
          ))}
        </aside>
        <main style={{ flex: 1, padding: 24, minWidth: 0 }}>
          <h1 style={{ marginTop: 0 }}>Dashboard</h1>
          <div className="card">
            <p style={{ marginTop: 0 }}>
              Slice 1 selesai di sini: gate password tunggal + dashboard ini.
            </p>
            <p className="muted">
              Canvas node akan dibangun di fase berikutnya. Menu di samping
              sengaja dinonaktifkan dan dilabeli “Segera hadir” — tidak ada
              fitur di baliknya yang berpura-pura berfungsi.
            </p>
          </div>
        </main>
      </div>
    </div>
  );
}
