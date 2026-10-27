"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiJson } from "@/lib/api";
import Shell from "@/components/Shell";

/** History: runs + frozen snapshot + per-node trace.
 * The snapshot shown here is the FROZEN graph version, not the live
 * graph — editing the canvas afterwards never rewrites this view. */
export default function HistoryPage() {
  const router = useRouter();
  const [checked, setChecked] = useState(false);
  const [runs, setRuns] = useState<any[]>([]);
  const [detail, setDetail] = useState<any>(null);

  useEffect(() => {
    apiJson("/api/auth/me").then((res) => {
      if (!res.ok) router.replace("/gate");
      else {
        setChecked(true);
        apiJson("/api/runs").then(async (r) => { if (r.ok) setRuns(await r.json()); });
      }
    }).catch(() => router.replace("/gate"));
  }, [router]);

  async function openRun(id: number) {
    const res = await apiJson(`/api/runs/${id}`);
    if (res.ok) setDetail(await res.json());
  }

  if (!checked) return <main style={{ padding: 24 }} className="muted">Memeriksa sesi…</main>;

  return (
    <Shell title="History">
      {runs.length === 0 && <p className="muted">Belum ada run. Buat dan jalankan graph di halaman Graph.</p>}
      <div style={{ display: "grid", gap: 10 }}>
        {runs.map((run) => (
          <button key={run.id} type="button" className="card" style={{ textAlign: "left", cursor: "pointer" }} onClick={() => openRun(run.id)}>
            <strong>Run #{run.id}</strong> · {run.status} · Graph #{run.graph_id} · {run.latency_ms} ms ·{" "}
            {run.usage_available ? `${run.token_in ?? "?"} in / ${run.token_out ?? "?"} out` : "token tidak tersedia dari provider"}
            <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>{(run.task_text || "").slice(0, 120)}</div>
          </button>
        ))}
      </div>
      {detail && (
        <div className="card" style={{ marginTop: 20 }}>
          <h3 style={{ marginTop: 0 }}>Run #{detail.id} — {detail.status}</h3>
          {detail.error && <p style={{ color: "#f87171" }}>{detail.error}</p>}
          <p className="muted">Versi graph beku: #{detail.graph_version?.version} · Hash: {(detail.graph_version?.content_hash || "").slice(0, 16)}…</p>
          <h4>Prompt rakitan final (Soul → System → Memory → Task)</h4>
          <pre style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{JSON.stringify(detail.assembled_prompt, null, 2)}</pre>
          <h4>Output mentah</h4>
          <pre style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{detail.output_text}</pre>
          <h4>Snapshot node beku (saat Run ditekan)</h4>
          <ul>
            {(detail.graph_version?.nodes || []).map((n: any) => (
              <li key={n.id}>{n.type} · {n.disabled ? "nonaktif" : "aktif"} · {(n.config.text || n.config.model || "").toString().slice(0, 80)}{n.type === "Model" ? ` · base_url: ${n.config.base_url || ""} · key: ${n.config.api_key_masked || "—"}` : ""}</li>
            ))}
          </ul>
          <h4>Trace per node</h4>
          <div style={{ display: "grid", gap: 8 }}>
            {detail.node_traces.map((t: any, i: number) => (
              <div key={i} style={{ border: "1px solid var(--border)", borderRadius: 8, padding: 10, fontSize: 14 }}>
                <strong>{t.type}</strong> ({t.node_id}) · {t.status} · token {t.tokens} · {t.duration_ms} ms
                {t.error && <div style={{ color: "#f87171" }}>{t.error}</div>}
                {t.input && <div className="muted">Input: {String(t.input).slice(0, 300)}</div>}
                {t.output && <div>Output: {String(t.output).slice(0, 300)}</div>}
              </div>
            ))}
          </div>
        </div>
      )}
    </Shell>
  );
}
