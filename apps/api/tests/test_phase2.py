"""Phase 2 tests: Model-node keys, frozen snapshots, semantic prompt
order, disabled nodes, run failures, comparisons, experiments.

LLM calls go to a LOCAL fake OpenAI-compatible server (threaded
http.server in this file) — no external provider is contacted, and no
real API key is used. The fake server records the messages it received
so prompt order can be asserted exactly.
"""

import json
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest


def _csrf(client):
    r = client.get("/api/auth/csrf")
    assert r.status_code == 200, r.text
    return r.json()["csrf_token"]


def _mut(client, method, path, payload=None):
    headers = {"X-CSRF-Token": _csrf(client)}
    if method == "POST":
        return client.post(path, json=payload, headers=headers)
    if method == "PUT":
        return client.put(path, json=payload, headers=headers)
    if method == "DELETE":
        return client.delete(path, headers=headers)
    raise ValueError(method)


@pytest.fixture()
def fake_provider():
    store = {"messages": [], "last_model": None}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _json(self, obj, code=200):
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/models":
                self._json({"data": [{"id": "fake-model-1"}, {"id": "fake-model-2"}]})
            else:
                self._json({"error": "not found"}, 404)

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
            if self.path == "/chat/completions":
                store["messages"] = payload.get("messages", [])
                store["last_model"] = payload.get("model")
                out = {"choices": [{"message": {"content": "FAKE-ANSWER"}}]}
                if payload.get("model") != "no-usage":
                    out["usage"] = {"prompt_tokens": 11, "completion_tokens": 5}
                self._json(out)
            else:
                self._json({"error": "not found"}, 404)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}", store
    finally:
        server.shutdown()
        server.server_close()


def _graph(name, base_url, model="fake-model-1", soul=None, system=None, memory=None,
           task="Jelaskan harness dalam satu kalimat.", disabled_soul=False):
    nodes = []
    edges = []

    def add(nid, ntype, x, text=None, extra=None):
        cfg = {}
        if text is not None:
            cfg["text"] = text
        if extra:
            cfg.update(extra)
        nodes.append({"id": nid, "type": ntype, "x": x, "y": 10, "config": cfg, "disabled": False})
        return nid

    # Deliberately scrambled canvas positions: prompt order must still
    # be Soul -> System -> Memory -> Task, never position order.
    add("soul", "Soul", 900, soul if soul is not None else "Kamu adalah mentor yang sabar.")
    add("sys", "SystemPrompt", 100, system if system is not None else "Jawab singkat dan konkret.")
    add("mem", "Memory", 500, memory if memory is not None else "Pengguna sedang belajar harness AI.")
    add("task", "Task", 0, task)
    model_cfg = {"base_url": base_url, "api_key": "sk-test-secret-1234", "model": model, "temperature": 0}
    nodes.append({"id": "model", "type": "Model", "x": 400, "y": 200, "config": model_cfg, "disabled": False})
    nodes.append({"id": "out", "type": "Output", "x": 700, "y": 200, "config": {}, "disabled": False})
    if disabled_soul:
        # A disabled Soul node with different text: must be skipped and
        # must NOT appear in the assembled prompt.
        nodes.append({"id": "soul-off", "type": "Soul", "x": 50, "y": 300,
                      "config": {"text": "SOUL-YANG-HARUS-DIABAIKAN"}, "disabled": True})
        edges.append({"id": "e-off", "from_node": "soul-off", "from_port": "out", "to_node": "model", "to_port": "soul"})
    edges += [
        {"id": "e1", "from_node": "soul", "from_port": "out", "to_node": "model", "to_port": "soul"},
        {"id": "e2", "from_node": "sys", "from_port": "out", "to_node": "model", "to_port": "system"},
        {"id": "e3", "from_node": "mem", "from_port": "out", "to_node": "model", "to_port": "memory"},
        {"id": "e4", "from_node": "task", "from_port": "out", "to_node": "model", "to_port": "task"},
        {"id": "e5", "from_node": "model", "from_port": "out", "to_node": "out", "to_port": "in"},
    ]
    return {"name": name, "nodes": nodes, "edges": edges}


def test_model_key_masked_never_returned_full_and_not_in_db(authed_client, fake_provider):
    base_url, _ = fake_provider
    r = _mut(authed_client, "POST", "/api/graphs", _graph("G1", base_url))
    assert r.status_code == 200, r.text
    model_node = [n for n in r.json()["nodes"] if n["type"] == "Model"][0]
    assert model_node["config"]["api_key"] == ""
    assert model_node["config"]["api_key_set"] is True
    assert "1234" in model_node["config"]["api_key_masked"]
    assert "sk-test-secret-1234" not in r.text
    # Raw DB content must not contain the plaintext key either.
    conn = sqlite3.connect("test_harlearn.db")
    try:
        rows = conn.execute("SELECT nodes_json FROM graphs").fetchall()
    finally:
        conn.close()
    assert rows, "expected at least one graph row"
    assert all("sk-test-secret-1234" not in row[0] for row in rows)
    assert any("api_key_enc" in row[0] for row in rows)


def test_resave_without_key_preserves_encrypted_key(authed_client, fake_provider):
    base_url, _ = fake_provider
    gid = _mut(authed_client, "POST", "/api/graphs", _graph("G2", base_url)).json()["id"]
    saved = authed_client.get(f"/api/graphs/{gid}").json()
    # Served api_key is ""; resaving exactly that must NOT wipe the key.
    for n in saved["nodes"]:
        n["config"]["api_key"] = ""
    r = _mut(authed_client, "PUT", f"/api/graphs/{gid}", saved)
    assert r.status_code == 200, r.text
    run = _mut(authed_client, "POST", "/api/runs", {"graph_id": gid})
    assert run.status_code == 200, run.text
    assert run.json()["status"] == "completed", run.json()
    assert run.json()["output_text"] == "FAKE-ANSWER"


def test_prompt_order_is_semantic_not_canvas_position(authed_client, fake_provider):
    base_url, store = fake_provider
    gid = _mut(authed_client, "POST", "/api/graphs", _graph("G3", base_url)).json()["id"]
    run = _mut(authed_client, "POST", "/api/runs", {"graph_id": gid}).json()
    assert run["status"] == "completed", run
    msgs = store["messages"]
    assert [m["role"] for m in msgs] == ["system", "system", "system", "user"]
    assert msgs[0]["content"] == "Kamu adalah mentor yang sabar."
    assert msgs[1]["content"] == "Jawab singkat dan konkret."
    assert msgs[2]["content"] == "Pengguna sedang belajar harness AI."
    assert msgs[3]["content"] == "Jelaskan harness dalam satu kalimat."
    assert run["token_in"] == 11 and run["token_out"] == 5 and run["usage_available"] is True


def test_disabled_node_skipped_with_zero_tokens(authed_client, fake_provider):
    base_url, store = fake_provider
    gid = _mut(authed_client, "POST", "/api/graphs",
               _graph("G4", base_url, disabled_soul=True)).json()["id"]
    run = _mut(authed_client, "POST", "/api/runs", {"graph_id": gid}).json()
    assert run["status"] == "completed", run
    assert all("SOUL-YANG-HARUS-DIABAIKAN" not in m["content"] for m in store["messages"])
    trace = {t["node_id"]: t for t in run["node_traces"]}
    assert trace["soul-off"]["status"] == "skipped"
    assert trace["soul-off"]["tokens"] == 0


def test_run_fails_clearly_when_model_not_connected_to_task(authed_client, fake_provider):
    base_url, _ = fake_provider
    payload = _graph("G5", base_url)
    payload["edges"] = [e for e in payload["edges"] if e["id"] != "e4"]  # drop Task -> Model
    gid = _mut(authed_client, "POST", "/api/graphs", payload).json()["id"]
    run = _mut(authed_client, "POST", "/api/runs", {"graph_id": gid}).json()
    assert run["status"] == "failed"
    assert "tidak terhubung" in run["error"]


def test_snapshot_frozen_and_comparison_detects_change(authed_client, fake_provider):
    base_url, _ = fake_provider
    gid = _mut(authed_client, "POST", "/api/graphs", _graph("G6", base_url)).json()["id"]
    run1 = _mut(authed_client, "POST", "/api/runs", {"graph_id": gid}).json()
    saved = authed_client.get(f"/api/graphs/{gid}").json()
    for n in saved["nodes"]:
        if n["id"] == "soul":
            n["config"]["text"] = "Kamu adalah mentor yang SANGAT sabar."
        n["config"]["api_key"] = ""
    _mut(authed_client, "PUT", f"/api/graphs/{gid}", saved)
    run2 = _mut(authed_client, "POST", "/api/runs", {"graph_id": gid}).json()
    assert run2["status"] == "completed", run2
    # run1's frozen version still holds the ORIGINAL soul text.
    detail1 = authed_client.get(f"/api/runs/{run1['id']}").json()
    frozen_soul = [n for n in detail1["graph_version"]["nodes"] if n["id"] == "soul"][0]
    assert frozen_soul["config"]["text"] == "Kamu adalah mentor yang sabar."
    assert detail1["assembled_prompt"][0]["content"] == "Kamu adalah mentor yang sabar."
    comp = authed_client.get(f"/api/comparisons?a={run1['id']}&b={run2['id']}").json()
    changed = {c["node_id"]: c for c in comp["diff"]["changed"]}
    assert "soul" in changed
    assert changed["soul"]["config_diff"]["text"]["from"] == "Kamu adalah mentor yang sabar."
    assert changed["soul"]["config_diff"]["text"]["to"] == "Kamu adalah mentor yang SANGAT sabar."
    assert comp["run_a"]["output_text"] == comp["run_b"]["output_text"] == "FAKE-ANSWER"


def test_fetch_models_is_transient(authed_client, fake_provider):
    base_url, _ = fake_provider
    before = authed_client.get("/api/graphs").json()
    r = _mut(authed_client, "POST", "/api/models/fetch",
             {"base_url": base_url, "api_key": "sk-transient-only"})
    assert r.status_code == 200, r.text
    assert r.json()["models"] == ["fake-model-1", "fake-model-2"]
    after = authed_client.get("/api/graphs").json()
    assert before == after, "fetch must not create or store anything"


def test_usage_unavailable_when_provider_omits_it(authed_client, fake_provider):
    base_url, _ = fake_provider
    gid = _mut(authed_client, "POST", "/api/graphs",
               _graph("G7", base_url, model="no-usage")).json()["id"]
    run = _mut(authed_client, "POST", "/api/runs", {"graph_id": gid}).json()
    assert run["status"] == "completed", run
    assert run["token_in"] is None and run["token_out"] is None
    assert run["usage_available"] is False


def test_experiment_and_rubric_scores(authed_client, fake_provider):
    base_url, _ = fake_provider
    gid = _mut(authed_client, "POST", "/api/graphs", _graph("G8", base_url)).json()["id"]
    run = _mut(authed_client, "POST", "/api/runs", {"graph_id": gid}).json()
    exp = _mut(authed_client, "POST", "/api/experiments", {
        "title": "Soul vs tanpa soul", "hypothesis": "Soul membuat jawaban lebih sabar.",
        "notes": "Kesimpulan awal: belum terlihat bedanya.", "run_ids": [run["id"]],
    }).json()
    assert exp["id"]
    score = _mut(authed_client, "POST", f"/api/experiments/{exp['id']}/scores", {
        "run_id": run["id"], "criterion": "Kejelasan", "score": 4, "note": "Jelas.",
    })
    assert score.status_code == 200, score.text
    detail = authed_client.get(f"/api/experiments/{exp['id']}").json()
    assert detail["run_ids"] == [run["id"]]
    assert detail["notes"] == "Kesimpulan awal: belum terlihat bedanya."
    assert detail["scores"][0]["criterion"] == "Kejelasan"
    assert detail["scores"][0]["score"] == 4


def test_new_pages_require_auth(client):
    assert client.get("/api/graphs").status_code == 401
    assert client.get("/api/runs").status_code == 401
    assert client.get("/api/experiments").status_code == 401
