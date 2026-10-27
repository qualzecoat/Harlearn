"""Graph execution (phase 2).

Semantic prompt order — NOT canvas position: Soul -> System Prompt ->
Memory as system messages, then Task as the user message. Canvas x/y
only affects display, never prompt order.

The Model node carries its own provider settings (base_url, api_key,
model, temperature). Execution reads the FROZEN version snapshot, so
editing the live graph afterwards cannot change a finished run.
"""

import time

import httpx

from . import crypto

NODE_TYPES = {"Task", "Soul", "SystemPrompt", "Memory", "Model", "Output"}
# to_port (or source-node type) -> semantic role feeding the Model node.
ROLE_BY_PORT = {"task": "task", "soul": "soul", "system": "system", "memory": "memory"}
ROLE_BY_TYPE = {"Task": "task", "Soul": "soul", "SystemPrompt": "system", "Memory": "memory"}
# Role -> position in the system-message order.
SYSTEM_ORDER = ["soul", "system", "memory"]


class RunError(Exception):
    pass


def _detect_cycle(nodes, edges):
    """Cycle check over enabled nodes only (disabled nodes are skipped)."""
    enabled = {n["id"] for n in nodes if not n.get("disabled")}
    adj = {nid: [] for nid in enabled}
    for e in edges:
        if e.get("from_node") in enabled and e.get("to_node") in enabled:
            adj[e["from_node"]].append(e["to_node"])
    visiting, done = set(), set()

    def visit(nid):
        if nid in done:
            return
        if nid in visiting:
            raise RunError("Graph mengandung siklus (cycle) — periksa kembali edge antar node.")
        visiting.add(nid)
        for nxt in adj.get(nid, []):
            visit(nxt)
        visiting.discard(nid)
        done.add(nid)

    for nid in enabled:
        visit(nid)


def validate_and_assemble(snapshot):
    """Return (model_node, messages, traces_skeleton, role_nodes).

    Raises RunError with a user-readable message for every invalid graph.
    """
    nodes = snapshot.get("nodes", [])
    edges = snapshot.get("edges", [])
    for n in nodes:
        if n.get("type") not in NODE_TYPES:
            raise RunError(f"Tipe node tidak dikenal: {n.get('type')}")
    _detect_cycle(nodes, edges)
    by_id = {n["id"]: n for n in nodes}
    enabled = [n for n in nodes if not n.get("disabled")]
    models = [n for n in enabled if n["type"] == "Model"]
    if len(models) == 0:
        raise RunError("Run membutuhkan 1 node Model yang aktif (tidak ditemukan).")
    if len(models) > 1:
        raise RunError(
            f"Run membutuhkan tepat 1 node Model yang aktif (ditemukan {len(models)}). "
            "Nonaktifkan node Model lainnya atau pisahkan ke graph lain."
        )
    model = models[0]
    # Inputs feeding the Model node, by semantic role.
    role_nodes = {}
    for e in edges:
        if e.get("to_node") != model["id"]:
            continue
        src = by_id.get(e.get("from_node"))
        if src is None or src.get("disabled"):
            continue
        role = ROLE_BY_PORT.get(e.get("to_port")) or ROLE_BY_TYPE.get(src["type"])
        if role is None or role in role_nodes:
            if role is not None:
                raise RunError(
                    f"Node Model hanya boleh menerima 1 node untuk peran '{role}' — "
                    "duplikasi peran membuat prompt ambigu."
                )
            continue
        role_nodes[role] = src
    task_node = role_nodes.get("task")
    if task_node is None:
        raise RunError(
            "Node Model tidak terhubung ke node Task yang aktif — "
            "hubungkan Task → Model (port 'task') sebelum Run."
        )
    task_text = str((task_node.get("config") or {}).get("text", "") or "").strip()
    if not task_text:
        raise RunError("Node Task yang terhubung masih kosong — isi teks tugasnya dulu.")
    model_cfg = model.get("config") or {}
    if not str(model_cfg.get("base_url", "") or "").strip():
        raise RunError("Node Model belum diisi base_url provider-nya.")
    if not str(model_cfg.get("model", "") or "").strip():
        raise RunError("Node Model belum diisi nama model-nya.")
    messages = []
    for role in SYSTEM_ORDER:
        node = role_nodes.get(role)
        if node is None:
            continue
        text = str((node.get("config") or {}).get("text", "") or "").strip()
        if text:
            messages.append({"role": "system", "content": text})
    messages.append({"role": "user", "content": task_text})
    return model, messages, role_nodes, task_text


def execute_run(snapshot):
    """Execute a frozen snapshot. Returns a dict for the Run row.

    Token usage comes ONLY from the provider response. If the provider
    does not return usage, token_in/token_out stay None and
    usage_available is False — no local estimate is ever presented as
    real usage.
    """
    started = time.monotonic()
    traces = []
    try:
        model, messages, role_nodes, task_text = validate_and_assemble(snapshot)
    except RunError as exc:
        for node in snapshot.get("nodes", []):
            traces.append(
                {
                    "node_id": node["id"],
                    "type": node["type"],
                    "input": "",
                    "output": "",
                    "tokens": 0,
                    "duration_ms": 0,
                    "status": "skipped" if node.get("disabled") else "failed",
                    "error": str(exc) if not node.get("disabled") else "",
                }
            )
        return {
            "status": "failed",
            "error": str(exc),
            "task_text": "",
            "assembled_prompt": [],
            "output_text": "",
            "token_in": None,
            "token_out": None,
            "usage_available": False,
            "latency_ms": int((time.monotonic() - started) * 1000),
            "traces": traces,
        }

    # Per-node traces for the assembly stage (all cheap, no LLM yet).
    used_ids = set()
    for role in SYSTEM_ORDER:
        node = role_nodes.get(role)
        if node is None:
            continue
        text = str((node.get("config") or {}).get("text", "") or "")
        traces.append(
            {
                "node_id": node["id"],
                "type": node["type"],
                "input": text,
                "output": text,
                "tokens": 0,
                "duration_ms": 0,
                "status": "completed",
                "error": "",
            }
        )
        used_ids.add(node["id"])
    traces.append(
        {
            "node_id": role_nodes["task"]["id"],
            "type": "Task",
            "input": task_text,
            "output": task_text,
            "tokens": 0,
            "duration_ms": 0,
            "status": "completed",
            "error": "",
        }
    )
    used_ids.add(role_nodes["task"]["id"])

    model_cfg = model.get("config") or {}
    base_url = str(model_cfg.get("base_url", "")).rstrip("/")
    try:
        temperature = float(model_cfg.get("temperature", 0.7))
    except (TypeError, ValueError):
        temperature = 0.7
    temperature = max(0.0, min(2.0, temperature))
    api_key = ""
    enc = model_cfg.get("api_key_enc", "")
    if enc:
        try:
            api_key = crypto.decrypt_api_key(enc)
        except ValueError as exc:
            return {
                "status": "failed",
                "error": f"Tidak bisa mendekripsi api_key node Model: {exc}",
                "task_text": task_text,
                "assembled_prompt": messages,
                "output_text": "",
                "token_in": None,
                "token_out": None,
                "usage_available": False,
                "latency_ms": int((time.monotonic() - started) * 1000),
                "traces": traces,
            }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    call_started = time.monotonic()
    try:
        # trust_env=False: see phase2.fetch_models for why env proxies
        # must not be inherited by provider calls.
        with httpx.Client(timeout=120.0, trust_env=False) as client:
            resp = client.post(
                f"{base_url}/chat/completions",
                json={
                    "model": model_cfg.get("model"),
                    "messages": messages,
                    "temperature": temperature,
                },
                headers=headers,
            )
    except httpx.HTTPError as exc:
        return {
            "status": "failed",
            "error": f"Tidak bisa menghubungi provider ({type(exc).__name__}: {exc})",
            "task_text": task_text,
            "assembled_prompt": messages,
            "output_text": "",
            "token_in": None,
            "token_out": None,
            "usage_available": False,
            "latency_ms": int((time.monotonic() - started) * 1000),
            "traces": traces,
        }
    call_ms = int((time.monotonic() - call_started) * 1000)
    if resp.status_code >= 400:
        body = resp.text[:500]
        result = {
            "status": "failed",
            "error": f"Provider mengembalikan HTTP {resp.status_code}: {body}",
            "task_text": task_text,
            "assembled_prompt": messages,
            "output_text": "",
            "token_in": None,
            "token_out": None,
            "usage_available": False,
            "latency_ms": int((time.monotonic() - started) * 1000),
            "traces": traces,
        }
        traces.append(
            {
                "node_id": model["id"],
                "type": "Model",
                "input": "",
                "output": "",
                "tokens": 0,
                "duration_ms": call_ms,
                "status": "failed",
                "error": result["error"],
            }
        )
        used_ids.add(model["id"])
        _append_unused_traces(snapshot, traces, used_ids)
        result["traces"] = traces
        return result
    try:
        payload = resp.json()
    except ValueError:
        return {
            "status": "failed",
            "error": "Provider mengembalikan respons yang bukan JSON.",
            "task_text": task_text,
            "assembled_prompt": messages,
            "output_text": "",
            "token_in": None,
            "token_out": None,
            "usage_available": False,
            "latency_ms": int((time.monotonic() - started) * 1000),
            "traces": traces,
        }
    choices = payload.get("choices") or []
    output_text = ""
    if choices:
        output_text = str(((choices[0].get("message") or {}).get("content") or ""))
    usage = payload.get("usage") or {}
    token_in = usage.get("prompt_tokens")
    token_out = usage.get("completion_tokens")
    usage_available = token_in is not None or token_out is not None
    traces.append(
        {
            "node_id": model["id"],
            "type": "Model",
            "input": "",
            "output": output_text,
            "tokens": (token_in or 0) + (token_out or 0) if usage_available else 0,
            "duration_ms": call_ms,
            "status": "completed",
            "error": "",
        }
    )
    used_ids.add(model["id"])
    # Output nodes fed by the Model node display its output.
    for node in snapshot.get("nodes", []):
        if node["type"] != "Output" or node.get("disabled"):
            continue
        fed = any(
            e.get("from_node") == model["id"] and e.get("to_node") == node["id"]
            for e in snapshot.get("edges", [])
        )
        if fed:
            traces.append(
                {
                    "node_id": node["id"],
                    "type": "Output",
                    "input": output_text,
                    "output": output_text,
                    "tokens": 0,
                    "duration_ms": 0,
                    "status": "completed",
                    "error": "",
                }
            )
            used_ids.add(node["id"])
    _append_unused_traces(snapshot, traces, used_ids)
    return {
        "status": "completed",
        "error": None,
        "task_text": task_text,
        "assembled_prompt": messages,
        "output_text": output_text,
        "token_in": token_in,
        "token_out": token_out,
        "usage_available": usage_available,
        "latency_ms": int((time.monotonic() - started) * 1000),
        "traces": traces,
    }


def _append_unused_traces(snapshot, traces, used_ids):
    for node in snapshot.get("nodes", []):
        if node["id"] in used_ids:
            continue
        traces.append(
            {
                "node_id": node["id"],
                "type": node["type"],
                "input": "",
                "output": "",
                "tokens": 0,
                "duration_ms": 0,
                "status": "skipped" if node.get("disabled") else "unused",
                "error": "",
            }
        )
