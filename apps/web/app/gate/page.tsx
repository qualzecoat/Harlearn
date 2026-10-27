"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiJson } from "@/lib/api";

/**
 * Gate page: password only. No registration, no username, no roles —
 * slice 1 is a single-password gate (see ARCHITECTURE.md).
 */
export default function GatePage() {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const res = await apiJson("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ password }),
      });
      if (!res.ok) {
        setError(res.status === 429 ? "Terlalu banyak percobaan. Tunggu 15 menit." : "Password salah.");
        return;
      }
      router.push("/");
      router.refresh();
    } catch {
      setError("API tidak dapat dihubungi. Periksa apakah backend berjalan.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: 16 }}>
      <div className="card" style={{ width: "100%", maxWidth: 400 }}>
        <h1 style={{ margin: "0 0 4px" }}>Harlearn</h1>
        <p className="muted" style={{ margin: "0 0 20px" }}>
          Lab AI — masukkan password aplikasi untuk membuka dashboard.
        </p>
        <form onSubmit={onSubmit} style={{ display: "grid", gap: 12 }}>
          <label>
            <span className="muted" style={{ fontSize: 13 }}>Password aplikasi</span>
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>
          {error && <p role="alert" style={{ color: "#f87171", margin: 0, fontSize: 14 }}>{error}</p>}
          <button className="btn" type="submit" disabled={busy}>
            {busy ? "Memeriksa…" : "Buka dashboard"}
          </button>
        </form>
        <p className="muted" style={{ fontSize: 12, margin: "16px 0 0" }}>
          Akses juga dibatasi ke jaringan Tailscale saja saat deploy.
        </p>
      </div>
    </main>
  );
}
