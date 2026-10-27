"""Phase 2 API: graphs (nodes), frozen versions, runs, experiments,
comparisons, and transient model fetching.

Provider settings live INSIDE Model nodes (corrected spec) — there is
no separate connection entity or /koneksi page. The fetch-models
endpoint receives base_url + api_key transiently and stores nothing.
"""

import hashlib
import json

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session as DbSession

from . import auth, config, executor, graph_keys
from .db import get_db
from .models import Experiment, ExperimentRun, Graph, GraphVersion, RubricScore, Run

router = APIRouter()


def _require_session(request: Request, db: DbSession):
    raw = request.cookies.get(config.COOKIE_NAME)
    row = auth.load_session(db, raw) if raw else None
    if row is None:
        raise HTTPException(status_code=401, detail="unauthenticated")
    return row


def _require_csrf(request: Request, row):
    csrf_header = request.headers.get("X-CSRF-Token", "")
    if not csrf_header or csrf_header != row.csrf_token:
        raise HTTPException(status_code=403, detail="invalid csrf token")


def _graph_or_404(db: DbSession, graph_id: int) -> Graph:
    row = db.query(Graph).filter(Graph.id == graph_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="graph not found")
    return row


def _run_or_404(db: DbSession, run_id: int) -> Run:
    row = db.query(Run).filter(Run.id == run_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="run not found")
    return row


def _serve_graph(row: Graph) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "nodes": graph_keys.served_nodes(json.loads(row.nodes_json or "[]")),
        "edges": json.loads(row.edges_json or "[]"),
    }


def _serve_run(row: Run) -> dict:
    return {
        "id": row.id,
        "graph_id": row.graph_id,
        "graph_version_id": row.graph_version_id,
        "task_text": row.task_text,
        "assembled_prompt": json.loads(row.assembled_prompt_json or "[]"),
        "output_text": row.output_text,
        "token_in": row.token_in,
        "token_out": row.token_out,
        "usage_available": row.usage_available,
        "latency_ms": row.latency_ms,
        "status": row.status,
        "error": row.error,
        "node_traces": json.loads(row.node_traces_json or "[]"),
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _serve_version(row: GraphVersion) -> dict:
    snapshot = json.loads(row.snapshot_json or "{}")
    return {
        "id": row.id,
        "graph_id": row.graph_id,
        "version": row.version,
        "content_hash": row.content_hash,
        # Served form: Model api_keys are masked/empty, never plaintext.
        "nodes": graph_keys.served_nodes(snapshot.get("nodes", [])),
        "edges": snapshot.get("edges", []),
    }


# ---------------------------------------------------------------- models
class FetchModelsBody(BaseModel):
    base_url: str
    api_key: str = ""


@router.post("/api/models/fetch")
def fetch_models(body: FetchModelsBody, request: Request, db: DbSession = Depends(get_db)):
    """Transient only: fetches {base_url}/models and stores NOTHING.

    The api_key here is used for this one request and then discarded;
    it is never written to the database, logs, or a graph.
    """
    row = _require_session(request, db)
    _require_csrf(request, row)
    base = (body.base_url or "").strip().rstrip("/")
    if not (base.startswith("http://") or base.startswith("https://")):
        raise HTTPException(status_code=400, detail="base_url harus diawali http:// atau https://")
    headers = {}
    if body.api_key:
        headers["Authorization"] = f"Bearer {body.api_key}"
    try:
        # trust_env=False: provider calls must NOT inherit the host's
        # HTTP(S)_PROXY env vars (this VM's egress proxy breaks httpx
        # URL parsing and would route provider traffic the wrong way).
        with httpx.Client(timeout=15.0, trust_env=False) as client:
            resp = client.get(f"{base}/models", headers=headers)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"tidak bisa menghubungi provider: {exc}") from exc
    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"provider mengembalikan HTTP {resp.status_code}")
    try:
        data = resp.json().get("data") or []
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="provider mengembalikan respons bukan JSON") from exc
    return {"models": [str(d.get("id")) for d in data if d.get("id")]}


# ---------------------------------------------------------------- graphs
class GraphBody(BaseModel):
    name: str
    nodes: list = []
    edges: list = []


@router.get("/api/graphs")
def list_graphs(request: Request, db: DbSession = Depends(get_db)):
    _require_session(request, db)
    rows = db.query(Graph).order_by(Graph.id.desc()).all()
    return [{"id": r.id, "name": r.name} for r in rows]


@router.post("/api/graphs")
def create_graph(body: GraphBody, request: Request, db: DbSession = Depends(get_db)):
    row = _require_session(request, db)
    _require_csrf(request, row)
    try:
        stored = graph_keys.stored_nodes(body.nodes, {})
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    graph = Graph(
        name=body.name or "Graph tanpa nama",
        nodes_json=json.dumps(stored),
        edges_json=json.dumps(body.edges),
    )
    db.add(graph)
    db.commit()
    db.refresh(graph)
    return _serve_graph(graph)


@router.get("/api/graphs/{graph_id}")
def get_graph(graph_id: int, request: Request, db: DbSession = Depends(get_db)):
    _require_session(request, db)
    return _serve_graph(_graph_or_404(db, graph_id))


@router.put("/api/graphs/{graph_id}")
def update_graph(graph_id: int, body: GraphBody, request: Request, db: DbSession = Depends(get_db)):
    row = _require_session(request, db)
    _require_csrf(request, row)
    graph = _graph_or_404(db, graph_id)
    old_nodes = json.loads(graph.nodes_json or "[]")
    old_by_id = {n["id"]: n for n in old_nodes}
    try:
        stored = graph_keys.stored_nodes(body.nodes, old_by_id)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    graph.name = body.name or graph.name
    graph.nodes_json = json.dumps(stored)
    graph.edges_json = json.dumps(body.edges)
    db.commit()
    db.refresh(graph)
    return _serve_graph(graph)


@router.delete("/api/graphs/{graph_id}")
def delete_graph(graph_id: int, request: Request, db: DbSession = Depends(get_db)):
    row = _require_session(request, db)
    _require_csrf(request, row)
    graph = _graph_or_404(db, graph_id)
    db.delete(graph)
    db.commit()
    return {"deleted": True}


@router.get("/api/graphs/{graph_id}/versions")
def list_versions(graph_id: int, request: Request, db: DbSession = Depends(get_db)):
    _require_session(request, db)
    _graph_or_404(db, graph_id)
    rows = (
        db.query(GraphVersion)
        .filter(GraphVersion.graph_id == graph_id)
        .order_by(GraphVersion.version.desc())
        .all()
    )
    return [_serve_version(r) for r in rows]


# ------------------------------------------------------------------- runs
class RunBody(BaseModel):
    graph_id: int


@router.post("/api/runs")
def create_run(body: RunBody, request: Request, db: DbSession = Depends(get_db)):
    row = _require_session(request, db)
    _require_csrf(request, row)
    graph = _graph_or_404(db, body.graph_id)
    stored_nodes = json.loads(graph.nodes_json or "[]")
    snapshot = {"nodes": stored_nodes, "edges": json.loads(graph.edges_json or "[]")}
    canonical = json.dumps(snapshot, sort_keys=True, ensure_ascii=False)
    content_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    count = db.query(GraphVersion).filter(GraphVersion.graph_id == graph.id).count()
    version = GraphVersion(
        graph_id=graph.id,
        version=count + 1,
        snapshot_json=json.dumps(snapshot),
        content_hash=content_hash,
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    # Execution reads ONLY the frozen snapshot, never the live graph.
    result = executor.execute_run(snapshot)
    run = Run(
        graph_id=graph.id,
        graph_version_id=version.id,
        task_text=result["task_text"],
        assembled_prompt_json=json.dumps(result["assembled_prompt"]),
        output_text=result["output_text"],
        token_in=result["token_in"],
        token_out=result["token_out"],
        usage_available=result["usage_available"],
        latency_ms=result["latency_ms"],
        status=result["status"],
        error=result["error"],
        node_traces_json=json.dumps(result["traces"]),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return _serve_run(run)


@router.get("/api/runs")
def list_runs(request: Request, db: DbSession = Depends(get_db)):
    _require_session(request, db)
    rows = db.query(Run).order_by(Run.id.desc()).limit(100).all()
    return [_serve_run(r) for r in rows]


@router.get("/api/runs/{run_id}")
def get_run(run_id: int, request: Request, db: DbSession = Depends(get_db)):
    _require_session(request, db)
    run = _run_or_404(db, run_id)
    version = db.query(GraphVersion).filter(GraphVersion.id == run.graph_version_id).first()
    data = _serve_run(run)
    data["graph_version"] = _serve_version(version) if version else None
    return data


# ------------------------------------------------------------ comparisons
def _diff_versions(a: dict, b: dict) -> dict:
    """Diff two served version snapshots.

    Nodes are matched by id (the edit-in-place A/B workflow). A second,
    by-type summary is included because duplicated graphs get new ids:
    it reports, per node type present in both, whether any config differs.
    """
    a_nodes = {n["id"]: n for n in a.get("nodes", [])}
    b_nodes = {n["id"]: n for n in b.get("nodes", [])}
    added = [n for nid, n in b_nodes.items() if nid not in a_nodes]
    removed = [n for nid, n in a_nodes.items() if nid not in b_nodes]
    changed = []
    for nid in a_nodes:
        if nid not in b_nodes:
            continue
        if a_nodes[nid].get("config") != b_nodes[nid].get("config") or a_nodes[nid].get("disabled") != b_nodes[nid].get("disabled"):
            diffs = {}
            a_cfg, b_cfg = a_nodes[nid].get("config") or {}, b_nodes[nid].get("config") or {}
            for key in sorted(set(a_cfg) | set(b_cfg)):
                if a_cfg.get(key) != b_cfg.get(key):
                    diffs[key] = {"from": a_cfg.get(key), "to": b_cfg.get(key)}
            changed.append(
                {
                    "node_id": nid,
                    "type": a_nodes[nid].get("type"),
                    "disabled_changed": a_nodes[nid].get("disabled") != b_nodes[nid].get("disabled"),
                    "config_diff": diffs,
                }
            )
    by_type = {}
    for t in sorted({n.get("type") for n in a.get("nodes", [])} & {n.get("type") for n in b.get("nodes", [])}):
        a_cfgs = [n.get("config") for n in a["nodes"] if n.get("type") == t]
        b_cfgs = [n.get("config") for n in b["nodes"] if n.get("type") == t]
        by_type[t] = {"config_differs": a_cfgs != b_cfgs}
    a_edges = {json.dumps(e, sort_keys=True) for e in a.get("edges", [])}
    b_edges = {json.dumps(e, sort_keys=True) for e in b.get("edges", [])}
    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "by_type": by_type,
        "edges_added": len(b_edges - a_edges),
        "edges_removed": len(a_edges - b_edges),
    }


@router.get("/api/comparisons")
def compare_runs(a: int, b: int, request: Request, db: DbSession = Depends(get_db)):
    _require_session(request, db)
    run_a = _run_or_404(db, a)
    run_b = _run_or_404(db, b)
    ver_a = db.query(GraphVersion).filter(GraphVersion.id == run_a.graph_version_id).first()
    ver_b = db.query(GraphVersion).filter(GraphVersion.id == run_b.graph_version_id).first()
    diff = _diff_versions(
        _serve_version(ver_a) if ver_a else {"nodes": [], "edges": []},
        _serve_version(ver_b) if ver_b else {"nodes": [], "edges": []},
    )
    return {"run_a": _serve_run(run_a), "run_b": _serve_run(run_b), "diff": diff}


# ------------------------------------------------------------ experiments
class ExperimentBody(BaseModel):
    title: str
    hypothesis: str = ""
    notes: str = ""
    run_ids: list = []


class ScoreBody(BaseModel):
    run_id: int
    criterion: str
    score: int
    note: str = ""


@router.get("/api/experiments")
def list_experiments(request: Request, db: DbSession = Depends(get_db)):
    _require_session(request, db)
    rows = db.query(Experiment).order_by(Experiment.id.desc()).all()
    return [{"id": r.id, "title": r.title, "hypothesis": r.hypothesis, "notes": r.notes} for r in rows]


@router.post("/api/experiments")
def create_experiment(body: ExperimentBody, request: Request, db: DbSession = Depends(get_db)):
    row = _require_session(request, db)
    _require_csrf(request, row)
    exp = Experiment(title=body.title, hypothesis=body.hypothesis, notes=body.notes)
    db.add(exp)
    db.commit()
    db.refresh(exp)
    for rid in body.run_ids:
        if db.query(Run).filter(Run.id == rid).first() is not None:
            db.add(ExperimentRun(experiment_id=exp.id, run_id=rid))
    db.commit()
    return {"id": exp.id, "title": exp.title, "hypothesis": exp.hypothesis, "notes": exp.notes, "run_ids": body.run_ids}


@router.get("/api/experiments/{exp_id}")
def get_experiment(exp_id: int, request: Request, db: DbSession = Depends(get_db)):
    _require_session(request, db)
    exp = db.query(Experiment).filter(Experiment.id == exp_id).first()
    if exp is None:
        raise HTTPException(status_code=404, detail="experiment not found")
    run_ids = [r.run_id for r in db.query(ExperimentRun).filter(ExperimentRun.experiment_id == exp_id).all()]
    scores = db.query(RubricScore).filter(RubricScore.experiment_id == exp_id).all()
    return {
        "id": exp.id,
        "title": exp.title,
        "hypothesis": exp.hypothesis,
        "notes": exp.notes,
        "run_ids": run_ids,
        "scores": [
            {"run_id": s.run_id, "criterion": s.criterion, "score": s.score, "note": s.note} for s in scores
        ],
    }


@router.put("/api/experiments/{exp_id}")
def update_experiment(exp_id: int, body: ExperimentBody, request: Request, db: DbSession = Depends(get_db)):
    row = _require_session(request, db)
    _require_csrf(request, row)
    exp = db.query(Experiment).filter(Experiment.id == exp_id).first()
    if exp is None:
        raise HTTPException(status_code=404, detail="experiment not found")
    exp.title = body.title or exp.title
    exp.hypothesis = body.hypothesis
    exp.notes = body.notes
    db.commit()
    return {"id": exp.id, "title": exp.title, "hypothesis": exp.hypothesis, "notes": exp.notes}


@router.post("/api/experiments/{exp_id}/scores")
def add_score(exp_id: int, body: ScoreBody, request: Request, db: DbSession = Depends(get_db)):
    row = _require_session(request, db)
    _require_csrf(request, row)
    if db.query(Experiment).filter(Experiment.id == exp_id).first() is None:
        raise HTTPException(status_code=404, detail="experiment not found")
    if not (0 <= body.score <= 5):
        raise HTTPException(status_code=400, detail="score harus 0–5")
    score = RubricScore(
        experiment_id=exp_id, run_id=body.run_id, criterion=body.criterion, score=body.score, note=body.note
    )
    db.add(score)
    db.commit()
    return {"ok": True}
