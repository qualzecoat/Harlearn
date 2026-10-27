"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiJson, apiMut } from "@/lib/api";
import Shell from "@/components/Shell";

/** Comparison: two runs side by side + graph diff + rubric + notes.
 * A/B is two runs (two graph versions), NOT two Soul nodes fighting
 * over one Model node in a single graph. Notes live in the experiment,
 * never inside a node. */
export default function ComparisonPage() {
  const router = useRouter();
  const [checked, setChecked] = useState(false);
  const [runs, setRuns] = useState<any[]>([]);
  const [a, setA] = useState("");
  const [b, setB] = useState("");
  const [comp, setComp] = useState<any>(null);
  const [message, setMessage] = useState("");
  const [expTitle, setExpTitle] = useState("");
  const [expHypothesis, setExpHypothesis] = useState("");
  const [expNotes, setExpNotes] = useState("");
  const [expId, setExpId] = useState<number | null>(null);
  const [scoreRun, setScoreRun] = useState("");
  const [criterion, setCriterion] = useState("Kejelasan");
  const [score, setScore] = useState(4);
  const [scoreNote, setScoreNote] = useState("");

  useEffect(() => {
    apiJson("/api/auth/me").then((res) => {
      if (!res.ok) router.replace("/gate");
      else {
        setChecked(true);
        apiJson("/api/runs").then(async (r) => { if (r.ok) setRuns(await r.json()); });
      }
    }).catch(() => router.replace("/gate"));
  }, [router]);

  async function compare() {
    if (!a || !b || a === b) { setMessage("Pilih dua run yang berbeda."); return; }
    const res = await apiJson(`/api/comparisons?a=${a}&b=${b}`);
    if (!res.ok) { setMessage(`Perbandingan gagal: ${res.status}`); return; }
    setComp(await res.json());
    setMessage("");
  }

  async function createExperiment() {
    if (!a || !b) { setMessage("Pilih dua run dulu."); return; }
    const res = await apiMut("/api/experiments", "POST", {
      title: expTitle || `Perbandingan run ${a} vs ${b}`,
      hypothesis: expHypothesis,
      notes: expNotes,
      run_ids: [Number(a), Number(b)],
    });
    if (!res.ok) { setMessage(`Gagal membuat experiment: ${res.status}`); return; }
    const data = await res.json();
    setExpId(data.id);
    setMessage(`Experiment #${data.id} dibuat. Catatan kesimpulan tersimpan di experiment, bukan di node.`);
  }

  async function addScore() {
    if (!expId || !scoreRun) { setMessage("Buat experiment dan pilih run untuk skor."); return; }
    const res = await apiMut(`/api/experiments/${expId}/scores`, "POST", {
      run_id: Number(scoreRun), criterion, score, note: scoreNote,
    });
    setMessage(res.ok ? "Skor rubrik tersimpan." : `Gagal menyimpan skor: ${res.status}`);
  }

  if (!checked) return <main style={{ padding: 24 }} className="muted">Memeriksa sesi…</main>;

  return (
    <Shell title="Perbandingan">
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
        <select value={a} onChange={(e) => setA(e.target.value)} style={{ maxWidth: 260 }}>
          <option value="">— Run A —</option>
          {runs.map((r) => <option key={r.id} value={r.id}>Run #{r.id} · {r.status} · Graph #{r.graph_id}</option>)}
        </select>
        <select value={b} onChange={(e) => setB(e.target.value)} style={{ maxWidth: 260 }}>
          <option value="">— Run B —</option>
          {runs.map((r) => <option key={r.id} value={r.id}>Run #{r.id} · {r.status} · Graph #{r.graph_id}</option>)}
        </select>
        <button className="btn" type="button" onClick={compare}>Bandingkan</button>
      </div>
      {message && <p className="muted">{message}</p>}
      {comp && (
        <>
          <div className="card" style={{ marginTop: 16 }}>
            <h3 style={{ marginTop: 0 }}>Diff graph</h3>
            <p className="muted">Node ditambah: {comp.diff.added.length} · dihapus: {comp.diff.removed.length} · berubah: {comp.diff.changed.length} · edge ditambah/dihapus: {comp.diff.edges_added}/{comp.diff.edges_removed}</p>
            {comp.diff.changed.map((c: any) => (
              <div key={c.node_id} style={{ marginBottom: 8 }}>
                <strong>{c.type}</strong> ({c.node_id}) berubah:
                <pre style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(c.config_diff, null, 2)}</pre>
              </div>
            ))}
            {comp.diff.added.map((n: any) => <div key={n.id}>+ {n.type} ({n.id})</div>)}
            {comp.diff.removed.map((n: any) => <div key={n.id}>− {n.type} ({n.id})</div>)}
            <p className="muted">Ringkasan per tipe (berguna bila graph diduplikasi sehingga id node baru): {JSON.stringify(comp.diff.by_type)}</p>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginTop: 16 }}>
            {[comp.run_a, comp.run_b].map((run: any) => (
              <div key={run.id} className="card">
                <h3 style={{ marginTop: 0 }}>Run #{run.id} — {run.status}</h3>
                <p className="muted">Token: {run.usage_available ? `${run.token_in ?? "?"} in / ${run.token_out ?? "?"} out` : "tidak tersedia dari provider"} · Latensi: {run.latency_ms} ms</p>
                {run.error && <p style={{ color: "#f87171" }}>{run.error}</p>}
                <pre style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{run.output_text}</pre>
              </div>
            ))}
          </div>
          <div className="card" style={{ marginTop: 16, display: "grid", gap: 10 }}>
            <h3 style={{ marginTop: 0 }}>Experiment &amp; rubrik (catatan di sini, bukan di node)</h3>
            <input value={expTitle} onChange={(e) => setExpTitle(e.target.value)} placeholder="Judul experiment" />
            <textarea value={expHypothesis} onChange={(e) => setExpHypothesis(e.target.value)} placeholder="Hipotesis: apa yang kamu harapkan berubah?" />
            <textarea value={expNotes} onChange={(e) => setExpNotes(e.target.value)} placeholder="Catatan kesimpulan" />
            <button className="btn" type="button" onClick={createExperiment}>Simpan sebagai experiment</button>
            {expId && (
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
                <span className="muted">Experiment #{expId} · Skor untuk run:</span>
                <select value={scoreRun} onChange={(e) => setScoreRun(e.target.value)} style={{ maxWidth: 180 }}>
                  <option value="">— Run —</option>
                  <option value={a}>Run #{a}</option>
                  <option value={b}>Run #{b}</option>
                </select>
                <input value={criterion} onChange={(e) => setCriterion(e.target.value)} style={{ maxWidth: 180 }} placeholder="Kriteria" />
                <input type="number" min={0} max={5} value={score} onChange={(e) => setScore(Number(e.target.value))} style={{ maxWidth: 90 }} />
                <input value={scoreNote} onChange={(e) => setScoreNote(e.target.value)} placeholder="Catatan skor" />
                <button className="btn-ghost" type="button" onClick={addScore}>Simpan skor</button>
              </div>
            )}
          </div>
        </>
      )}
    </Shell>
  );
}
