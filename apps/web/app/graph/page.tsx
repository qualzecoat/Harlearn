"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { apiJson, apiMut } from "@/lib/api";
import Shell from "@/components/Shell";

type NodeT = { id: string; type: string; x: number; y: number; config: Record<string, any>; disabled: boolean };
type EdgeT = { id: string; from_node: string; from_port: string; to_node: string; to_port: string };

const NODE_TYPES = ["Task", "Soul", "SystemPrompt", "Memory", "Model", "Output"];
const TYPE_LABEL: Record<string, string> = {
  Task: "Task", Soul: "Soul", SystemPrompt: "System Prompt", Memory: "Memory", Model: "Model", Output: "Output",
};
const TYPE_HELP: Record<string, string> = {
  Task: "Teks tugas yang dikirim sebagai user message. Wajib terhubung ke node Model (port task).",
  Soul: "Identitas/persona, dikirim sebagai system message pertama. Hubungkan ke node Model (port soul).",
  SystemPrompt: "Instruksi sistem, dikirim sebagai system message kedua. Hubungkan ke node Model (port system).",
  Memory: "Konteks/memori, dikirim sebagai system message ketiga. Hubungkan ke node Model (port memory).",
  Model: "Satu-satunya node yang memanggil provider. Isi base_url, api_key, model, dan temperature di sini. Tidak ada koneksi terpisah.",
  Output: "Penampil hasil. Hubungkan dari node Model (out → in).",
};
const MODEL_IN_PORTS = ["task", "soul", "system", "memory"];

function uid() {
  return `n${Date.now().toString(36)}${Math.floor(Math.random() * 1e6).toString(36)}`;
}

function defaultConfig(type: string): Record<string, any> {
  if (type === "Model") return { base_url: "", api_key: "", model: "", temperature: 0.7 };
  if (type === "Output") return {};
  return { text: "" };
}

export default function GraphPage() {
  const router = useRouter();
  const [checked, setChecked] = useState(false);
  const [graphId, setGraphId] = useState<number | null>(null);
  const [graphName, setGraphName] = useState("Graph baru");
  const [graphList, setGraphList] = useState<{ id: number; name: string }[]>([]);
  const [nodes, setNodes] = useState<NodeT[]>([]);
  const [edges, setEdges] = useState<EdgeT[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [inspectorTab, setInspectorTab] = useState<"config" | "trace" | "help">("config");
  const [menu, setMenu] = useState<{ x: number; y: number; nodeId: string | null } | null>(null);
  const [clipboard, setClipboard] = useState<NodeT | null>(null);
  const [pending, setPending] = useState<{ nodeId: string; port: string } | null>(null);
  const [message, setMessage] = useState("");
  const [lastRun, setLastRun] = useState<any>(null);
  const [running, setRunning] = useState(false);
  const [modelList, setModelList] = useState<string[]>([]);
  const dragRef = useRef<{ id: string; dx: number; dy: number } | null>(null);

  useEffect(() => {
    apiJson("/api/auth/me").then((res) => {
      if (!res.ok) router.replace("/gate");
      else {
        setChecked(true);
        refreshList();
      }
    }).catch(() => router.replace("/gate"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router]);

  useEffect(() => {
    const move = (e: MouseEvent) => {
      if (!dragRef.current) return;
      const { id, dx, dy } = dragRef.current;
      setNodes((prev) => prev.map((n) => (n.id === id ? { ...n, x: Math.max(0, e.clientX - dx), y: Math.max(0, e.clientY - dy) } : n)));
    };
    const up = () => { dragRef.current = null; };
    window.addEventListener("mousemove", move);
    window.addEventListener("mouseup", up);
    return () => { window.removeEventListener("mousemove", move); window.removeEventListener("mouseup", up); };
  }, []);

  async function refreshList() {
    const res = await apiJson("/api/graphs");
    if (res.ok) setGraphList(await res.json());
  }

  function addNode(type: string, x: number, y: number) {
    const node: NodeT = { id: uid(), type, x: Math.max(0, x - 110), y: Math.max(0, y - 20), config: defaultConfig(type), disabled: false };
    setNodes((prev) => [...prev, node]);
    setSelectedId(node.id);
    setMenu(null);
  }

  function updateNode(id: string, patch: Partial<NodeT>) {
    setNodes((prev) => prev.map((n) => (n.id === id ? { ...n, ...patch } : n)));
  }

  function updateConfig(id: string, key: string, value: any) {
    setNodes((prev) => prev.map((n) => (n.id === id ? { ...n, config: { ...n.config, [key]: value } } : n)));
  }

  async function saveGraph() {
    setMessage("");
    const payload = { name: graphName, nodes, edges };
    const res = graphId
      ? await apiMut(`/api/graphs/${graphId}`, "PUT", payload)
      : await apiMut("/api/graphs", "POST", payload);
    if (!res.ok) { setMessage(`Gagal menyimpan: ${res.status} — ${(await res.text()).slice(0, 300)}`); return; }
    const data = await res.json();
    setGraphId(data.id);
    setGraphName(data.name);
    setNodes(data.nodes);
    setEdges(data.edges);
    setMessage(`Graph tersimpan (id ${data.id}). Key Model yang tidak diubah dipertahankan.`);
    refreshList();
  }

  async function loadGraph(id: number) {
    const res = await apiJson(`/api/graphs/${id}`);
    if (!res.ok) return;
    const data = await res.json();
    setGraphId(data.id);
    setGraphName(data.name);
    setNodes(data.nodes);
    setEdges(data.edges);
    setSelectedId(null);
    setLastRun(null);
  }

  async function runGraph() {
    if (!graphId) { setMessage("Simpan graph dulu sebelum Run."); return; }
    setRunning(true);
    setMessage("");
    const res = await apiMut("/api/runs", "POST", { graph_id: graphId });
    setRunning(false);
    if (!res.ok) { setMessage(`Run gagal dikirim: ${res.status}`); return; }
    const data = await res.json();
    setLastRun(data);
    setMessage(data.status === "completed" ? `Run ${data.id} selesai.` : `Run ${data.id} gagal: ${data.error || "unknown"}`);
  }

  async function fetchModels(node: NodeT) {
    if (!node.config.base_url) { setMessage("Isi base_url dulu sebelum fetch model."); return; }
    const res = await apiMut("/api/models/fetch", "POST", { base_url: node.config.base_url, api_key: node.config.api_key || "" });
    if (!res.ok) { setMessage(`Fetch model gagal: ${res.status}`); return; }
    const data = await res.json();
    setModelList(data.models || []);
    setMessage(`Ditemukan ${(data.models || []).length} model (tidak disimpan apa pun oleh endpoint ini).`);
  }

  const selected = nodes.find((n) => n.id === selectedId) || null;
  const selectedTrace = lastRun?.node_traces?.find((t: any) => t.node_id === selectedId);

  function nodeCenterLeft(n: NodeT) { return { x: n.x, y: n.y + 46 }; }
  function nodeCenterRight(n: NodeT) { return { x: n.x + 220, y: n.y + 46 }; }

  if (!checked) return <main style={{ padding: 24 }} className="muted">Memeriksa sesi…</main>;

  return (
    <Shell title="Graph">
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center", marginBottom: 12 }}>
        <input value={graphName} onChange={(e) => setGraphName(e.target.value)} style={{ maxWidth: 260 }} placeholder="Nama graph" />
        <button className="btn" type="button" onClick={saveGraph}>Save Graph</button>
        <select
          value={graphId ?? ""}
          onChange={(e) => e.target.value && loadGraph(Number(e.target.value))}
          style={{ maxWidth: 260 }}
        >
          <option value="">— Load graph tersimpan —</option>
          {graphList.map((g) => <option key={g.id} value={g.id}>{g.name} (#{g.id})</option>)}
        </select>
        <button className="btn-ghost" type="button" onClick={() => { setGraphId(null); setGraphName("Graph baru"); setNodes([]); setEdges([]); setSelectedId(null); setLastRun(null); }}>Graph baru</button>
        <button className="btn" type="button" onClick={runGraph} disabled={running}>{running ? "Menjalankan…" : "Run"}</button>
      </div>
      {message && <p className="muted" style={{ marginTop: 0 }}>{message}</p>}
      {pending && (
        <p style={{ marginTop: 0 }}>
          Menghubungkan dari <strong>{pending.nodeId}</strong> ({pending.port}) — klik port input node tujuan, atau klik di sini untuk batal:{" "}
          <button className="btn-ghost" type="button" onClick={() => setPending(null)}>Batal</button>
        </p>
      )}
      <div style={{ display: "flex", gap: 16, alignItems: "flex-start" }}>
        {/* Canvas */}
        <div
          style={{ flex: 1, minWidth: 0, height: 640, overflow: "auto", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 12, position: "relative" }}
          onContextMenu={(e) => { e.preventDefault(); setMenu({ x: e.clientX, y: e.clientY, nodeId: null }); }}
          onClick={() => setMenu(null)}
        >
          <div style={{ position: "relative", width: 1400, height: 900 }}>
            <svg style={{ position: "absolute", inset: 0, width: 1400, height: 900, pointerEvents: "none" }}>
              {edges.map((e) => {
                const from = nodes.find((n) => n.id === e.from_node);
                const to = nodes.find((n) => n.id === e.to_node);
                if (!from || !to) return null;
                const a = nodeCenterRight(from);
                const b = nodeCenterLeft(to);
                return <line key={e.id} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="#a3e635" strokeWidth={2} />;
              })}
            </svg>
            {nodes.length === 0 && (
              <p className="muted" style={{ position: "absolute", left: 24, top: 24, maxWidth: 420 }}>
                Canvas kosong. Klik kanan di sini untuk Add Node, lalu hubungkan node ke node Model.
                Urutan prompt tidak ditentukan posisi canvas, melainkan semantik: Soul → System → Memory → Task.
              </p>
            )}
            {nodes.map((node) => (
              <div
                key={node.id}
                style={{
                  position: "absolute", left: node.x, top: node.y, width: 220,
                  background: selectedId === node.id ? "var(--surface-2)" : "var(--bg)",
                  border: `1px solid ${selectedId === node.id ? "var(--accent)" : "var(--border)"}`,
                  borderRadius: 10, opacity: node.disabled ? 0.55 : 1, cursor: "default",
                }}
                onClick={(e) => { e.stopPropagation(); setSelectedId(node.id); setMenu(null); }}
                onContextMenu={(e) => { e.preventDefault(); e.stopPropagation(); setSelectedId(node.id); setMenu({ x: e.clientX, y: e.clientY, nodeId: node.id }); }}
              >
                <div
                  style={{ padding: "8px 10px", borderBottom: "1px solid var(--border)", fontWeight: 700, cursor: "grab", display: "flex", justifyContent: "space-between" }}
                  onMouseDown={(e) => {
                    const rect = (e.currentTarget.parentElement as HTMLElement).getBoundingClientRect();
                    dragRef.current = { id: node.id, dx: e.clientX - rect.left, dy: e.clientY - rect.top };
                  }}
                >
                  <span>{TYPE_LABEL[node.type] || node.type}</span>
                  <span className="muted" style={{ fontWeight: 400, fontSize: 12 }}>{node.disabled ? "nonaktif" : ""}</span>
                </div>
                <div style={{ padding: "8px 10px", display: "flex", flexDirection: "column", gap: 6 }}>
                  {node.type !== "Task" && node.type !== "Output" && (
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                      {(node.type === "Model" ? MODEL_IN_PORTS : ["in"]).map((port) => (
                        <button
                          key={port}
                          type="button"
                          className="btn-ghost"
                          style={{ padding: "2px 8px", fontSize: 12 }}
                          onClick={(e) => {
                            e.stopPropagation();
                            if (!pending) return;
                            const exists = edges.some((ed) => ed.from_node === pending.nodeId && ed.to_node === node.id && ed.to_port === port);
                            if (!exists && pending.nodeId !== node.id) {
                              setEdges((prev) => [...prev, { id: uid(), from_node: pending.nodeId, from_port: pending.port, to_node: node.id, to_port: port }]);
                            }
                            setPending(null);
                          }}
                        >
                          ◉ {port}
                        </button>
                      ))}
                    </div>
                  )}
                  <div style={{ fontSize: 13 }} className="muted">
                    {node.type === "Model"
                      ? (node.config.model || "model belum diisi")
                      : node.type === "Output"
                        ? "Output run"
                        : ((node.config.text || "").slice(0, 60) || "kosong")}
                  </div>
                  {node.type !== "Output" && (
                    <div style={{ textAlign: "right" }}>
                      <button
                        type="button"
                        className="btn-ghost"
                        style={{ padding: "2px 8px", fontSize: 12 }}
                        onClick={(e) => { e.stopPropagation(); setPending({ nodeId: node.id, port: "out" }); }}
                      >
                        out ●
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
        {/* Inspector */}
        <div className="card" style={{ width: 340, flexShrink: 0 }}>
          <h3 style={{ marginTop: 0 }}>Inspector</h3>
          {!selected && <p className="muted">Klik sebuah node untuk mengeditnya, atau klik kanan untuk menu node.</p>}
          {selected && (
            <>
              <p style={{ marginTop: 0 }}><strong>{TYPE_LABEL[selected.type]}</strong> <span className="muted">· {selected.id}</span></p>
              <div style={{ display: "flex", gap: 6, marginBottom: 12 }}>
                {(["config", "trace", "help"] as const).map((tab) => (
                  <button key={tab} type="button" className="btn-ghost" onClick={() => setInspectorTab(tab)} style={{ borderColor: inspectorTab === tab ? "var(--accent)" : undefined }}>
                    {tab === "config" ? "Config" : tab === "trace" ? "Last Input-Output" : "Help"}
                  </button>
                ))}
              </div>
              {inspectorTab === "help" && <p className="muted">{TYPE_HELP[selected.type] || ""}</p>}
              {inspectorTab === "trace" && (
                selectedTrace ? (
                  <div style={{ fontSize: 14 }}>
                    <p>Status: <strong>{selectedTrace.status}</strong> · Token: {selectedTrace.tokens} · {selectedTrace.duration_ms} ms</p>
                    <p className="muted">Input</p><pre style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{String(selectedTrace.input || "")}</pre>
                    <p className="muted">Output</p><pre style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{String(selectedTrace.output || "")}</pre>
                    {selectedTrace.error && <p style={{ color: "#f87171" }}>{selectedTrace.error}</p>}
                  </div>
                ) : <p className="muted">Belum ada run untuk graph ini, atau node ini tidak terlibat di run terakhir.</p>
              )}
              {inspectorTab === "config" && selected.type !== "Output" && selected.type !== "Model" && (
                <label>
                  <span className="muted" style={{ fontSize: 13 }}>Teks</span>
                  <textarea value={selected.config.text || ""} onChange={(e) => updateConfig(selected.id, "text", e.target.value)} />
                </label>
              )}
              {inspectorTab === "config" && selected.type === "Output" && (
                <p className="muted">Output tidak punya config. Ia menampilkan hasil node Model yang terhubung.</p>
              )}
              {inspectorTab === "config" && selected.type === "Model" && (
                <div style={{ display: "grid", gap: 10 }}>
                  <label><span className="muted" style={{ fontSize: 13 }}>base_url</span>
                    <input value={selected.config.base_url || ""} onChange={(e) => updateConfig(selected.id, "base_url", e.target.value)} placeholder="https://contoh-provider/v1" /></label>
                  <label><span className="muted" style={{ fontSize: 13 }}>api_key {selected.config.api_key_set ? `(tersimpan: ${selected.config.api_key_masked || "••••"})` : "(belum ada)"}</span>
                    <input type="password" value={selected.config.api_key || ""} onChange={(e) => updateConfig(selected.id, "api_key", e.target.value)} placeholder="Kosongkan = pertahankan key tersimpan" /></label>
                  <p className="muted" style={{ fontSize: 12, margin: 0 }}>Key tidak pernah dikembalikan penuh oleh backend dan disimpan terenkripsi. Endpoint fetch model tidak menyimpan apa pun.</p>
                  <button className="btn-ghost" type="button" onClick={() => fetchModels(selected)}>Fetch model dari provider</button>
                  {modelList.length > 0 && (
                    <select value={selected.config.model || ""} onChange={(e) => updateConfig(selected.id, "model", e.target.value)}>
                      <option value="">— Pilih model —</option>
                      {modelList.map((m) => <option key={m} value={m}>{m}</option>)}
                    </select>
                  )}
                  <label><span className="muted" style={{ fontSize: 13 }}>model (atau ketik manual)</span>
                    <input value={selected.config.model || ""} onChange={(e) => updateConfig(selected.id, "model", e.target.value)} /></label>
                  <label><span className="muted" style={{ fontSize: 13 }}>temperature (0–2)</span>
                    <input type="number" min={0} max={2} step={0.1} value={selected.config.temperature ?? 0.7} onChange={(e) => updateConfig(selected.id, "temperature", Number(e.target.value))} /></label>
                </div>
              )}
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 14 }}>
                <button className="btn-ghost" type="button" onClick={() => updateNode(selected.id, { disabled: !selected.disabled })}>
                  {selected.disabled ? "Enable" : "Disable"}
                </button>
                <button className="btn-ghost" type="button" onClick={() => {
                  const copy = { ...selected, id: uid(), x: selected.x + 30, y: selected.y + 30 };
                  setNodes((prev) => [...prev, copy]); setSelectedId(copy.id);
                }}>Duplicate</button>
                <button className="btn-ghost" type="button" onClick={() => {
                  setNodes((prev) => prev.filter((n) => n.id !== selected.id));
                  setEdges((prev) => prev.filter((e) => e.from_node !== selected.id && e.to_node !== selected.id));
                  setSelectedId(null);
                }}>Delete</button>
              </div>
            </>
          )}
        </div>
      </div>
      {/* Context menu */}
      {menu && (
        <div
          className="card"
          style={{ position: "fixed", left: Math.min(menu.x, window.innerWidth - 260), top: Math.min(menu.y, window.innerHeight - 320), zIndex: 50, minWidth: 220 }}
          onClick={(e) => e.stopPropagation()}
        >
          {menu.nodeId === null ? (
            <>
              <p style={{ margin: "0 0 8px" }}><strong>Add Node</strong></p>
              {NODE_TYPES.map((t) => (
                <button key={t} type="button" className="btn-ghost" style={{ display: "block", width: "100%", textAlign: "left", marginBottom: 4 }} onClick={() => addNode(t, menu.x, menu.y)}>
                  {TYPE_LABEL[t]}
                </button>
              ))}
              {clipboard && (
                <button type="button" className="btn-ghost" style={{ display: "block", width: "100%", textAlign: "left" }} onClick={() => {
                  const copy = { ...clipboard, id: uid(), x: menu.x - 110, y: menu.y - 20 };
                  setNodes((prev) => [...prev, copy]); setMenu(null);
                }}>Paste ({TYPE_LABEL[clipboard.type]})</button>
              )}
            </>
          ) : (
            <>
              <p style={{ margin: "0 0 8px" }}><strong>Node menu</strong></p>
              {(() => {
                const node = nodes.find((n) => n.id === menu.nodeId);
                if (!node) return null;
                return (
                  <div style={{ display: "grid", gap: 4 }}>
                    <button type="button" className="btn-ghost" onClick={() => { const copy = { ...node, id: uid(), x: node.x + 30, y: node.y + 30 }; setNodes((prev) => [...prev, copy]); setSelectedId(copy.id); setMenu(null); }}>Duplicate</button>
                    <button type="button" className="btn-ghost" onClick={() => { setClipboard(node); setMenu(null); }}>Copy</button>
                    <button type="button" className="btn-ghost" onClick={() => { setClipboard(node); setNodes((prev) => prev.filter((n) => n.id !== node.id)); setEdges((prev) => prev.filter((e) => e.from_node !== node.id && e.to_node !== node.id)); setMenu(null); }}>Cut</button>
                    {clipboard && <button type="button" className="btn-ghost" onClick={() => { const copy = { ...clipboard, id: uid(), x: node.x + 30, y: node.y + 30 }; setNodes((prev) => [...prev, copy]); setMenu(null); }}>Paste</button>}
                    <button type="button" className="btn-ghost" onClick={() => { updateNode(node.id, { disabled: !node.disabled }); setMenu(null); }}>{node.disabled ? "Enable" : "Disable"}</button>
                    <button type="button" className="btn-ghost" onClick={() => { setNodes((prev) => prev.filter((n) => n.id !== node.id)); setEdges((prev) => prev.filter((e) => e.from_node !== node.id && e.to_node !== node.id)); setMenu(null); }}>Delete</button>
                  </div>
                );
              })()}
            </>
          )}
        </div>
      )}
      {/* Last run result */}
      {lastRun && (
        <div className="card" style={{ marginTop: 16 }}>
          <h3 style={{ marginTop: 0 }}>Hasil Run #{lastRun.id} — {lastRun.status}</h3>
          {lastRun.error && <p style={{ color: "#f87171" }}>{lastRun.error}</p>}
          <p className="muted">
            Token: {lastRun.usage_available ? `${lastRun.token_in ?? "?"} in / ${lastRun.token_out ?? "?"} out` : "tidak tersedia dari provider"} · Latensi: {lastRun.latency_ms} ms
          </p>
          <pre style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{lastRun.output_text}</pre>
          <p className="muted">Detail lengkap (prompt rakitan + trace per node + snapshot beku) ada di History.</p>
        </div>
      )}
    </Shell>
  );
}
