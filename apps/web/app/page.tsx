"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiJson } from "@/lib/api";
import Shell from "@/components/Shell";

/** Dashboard (phase 2): gate check + Shell. The canvas lives on /graph,
 * runs on /history, comparisons on /perbandingan. */
export default function DashboardPage() {
  const router = useRouter();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    apiJson("/api/auth/me").then((res) => {
      if (!res.ok) router.replace("/gate");
      else setChecked(true);
    }).catch(() => router.replace("/gate"));
  }, [router]);

  if (!checked) {
    return <main style={{ padding: 24 }} className="muted">Memeriksa sesi…</main>;
  }

  return (
    <Shell title="Dashboard">
      <div className="card">
        <p style={{ marginTop: 0 }}>
          Fase 2: lab node sudah aktif. Susun graph di halaman Graph,
          jalankan, lalu bandingkan run di History dan Perbandingan.
        </p>
        <p className="muted">
          Ingat modelnya: semua layer harness adalah node. “Profil”
          adalah graph yang disimpan, bukan form terpisah. Provider
          diatur di dalam node Model itu sendiri — tidak ada menu
          Koneksi terpisah. Benchmark masih “Segera hadir”.
        </p>
      </div>
    </Shell>
  );
}
