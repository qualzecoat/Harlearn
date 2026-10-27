# Harlearn — Project context

> This file is the AI context for the repo. Update it on every locked
> decision, exactly like PROJECT.md in the Lifunze repo.

## What Harlearn is

A solo AI lab for learning harnesses by direct comparison, and later for
benchmarking models/providers. The user learns best by seeing two runs
side by side when exactly one thing changes — not by reading definitions.

Core workflow (target, not slice 1):
1. Build a graph of nodes: Task, Soul, System Prompt, Memory, Model,
   Output. Provider settings (base URL + API key + model + temperature)
   live INSIDE the Model node — there is no separate provider-connection
   page or entity (corrected spec, 2026-10-28).
2. Assemble a harness from layers: soul, system prompt, memory, user
   profile, skills, tools/MCP, output schema/parser — each layer a node
   wired into the Model node.
3. Or load a preset from an agent (e.g. Hermes) — as a saved graph
   template, never as a live link to that agent's home directory.
4. Run the same task, save the run, compare runs, score them on a rubric.

## Locked decisions (2026-10-28)

- **Repo:** `qualzecoat/Harlearn` (public). Note the spelling: Harlearn,
  not Harlean.
- **Theme:** Graphite Volt (dark graphite + lime volt). See README.md for
  the exact tokens. Lifunze's violet + amber must NOT be reused.
- **UI pattern:** Lifunze-style layout (header, sidebar, cards) — the
  Impeccable design skill was considered and explicitly DROPPED by the user.
- **Auth:** Tailscale-only + **single app password**. No registration,
  no multi-user, no roles in slice 1. Gate = one Argon2-hashed password,
  HttpOnly session cookie, Lock/Logout button in the header.
- **Lab shape (future, corrected 2026-10-28 by the user):** node-style
  canvas like n8n/ComfyUI, and EVERY harness layer IS a node — Soul,
  System Prompt, Memory, Skill, etc. are nodes wired into a Model node.
  A "harness profile" is NOT a separate form: it is a SAVED GRAPH (a
  saved collection of nodes + connections). A preset such as Hermes is
  a saved graph template, not a live link. Canvas = recipe (graph);
  Run = execution of a frozen graph version; Experiment = a set of
  runs + rubric + notes. Recording lives in History/Experiments, not
  inside the canvas. Custom nodes are planned for later, not slice 1.
- **Provider settings live in the Model node (corrected 2026-10-28
  by the user):** there is NO separate provider-connection page or
  entity. Base URL, API key, model fetch, and model choice are all
  Model-node settings. A Model node's API key is stored
  Fernet-encrypted, displayed masked, and never returned in full;
  a saved graph that is re-saved without changing the key keeps
  the existing encrypted key.
- **Comparison model (clarified 2026-10-28):** compare two RUNS from
  two graphs/versions, side by side — not two competing nodes inside
  one graph. Each run stores a frozen snapshot of the whole graph
  (every node's config at run time) plus a per-node execution trace
  (input, output, tokens, duration), so clicking a node in History
  shows what it contained THEN, not what it contains now. The
  comparison view shows, top to bottom: graph diff (which nodes
  changed/added/removed, with config diffs), the two outputs side
  by side, metrics (tokens, latency), rubric scores, and the
  experiment's conclusion note.
- **Stack:** Next.js (web) + FastAPI (API) + PostgreSQL, monorepo,
  Docker Compose on the user's Sirius VPS, published only on the
  Tailscale IP. No public ports.
- **Technical language:** the user explicitly wants technical terms used
  as-is and will ask when something is unclear. When AI behaviour
  changes, name the harness layer that changed.

## Slice 1 (built locally; push + deploy 2026-10-28)

Gate password tunggal + dashboard shell (header “Harlearn · Lab AI” +
Lock button + disabled, honestly-labelled sidebar skeleton). Backend:
FastAPI auth endpoints, server-side sessions + CSRF, Alembic 0001
(`sessions`, `settings`). See ARCHITECTURE.md for the verified test
results and for what was NOT verified in this environment (no Docker,
no PostgreSQL here — migration was verified on SQLite only).

Update rule (user instruction 2026-10-28): this file MUST be updated
on every locked decision and every deploy, without exception.

## Deploy log

- 2026-10-28 — Slice 1: initial commit pushed to `main`, deploy to
  Sirius started (details + verification to be appended once the
  Tailscale gate check passes).
- 2026-10-28 — Deploy fixes (found on first Sirius build, before any
  container went live): (1) web Dockerfile now copies
  `package-lock.json` alongside `package.json` — `npm ci` previously
  failed without it; (2) Argon2 PHC hashes must be `$$`-escaped in
  `.env` because Docker Compose interpolates `$argon2id`/`$v`/`$m` as
  variables and corrupts the hash — see `.env.example`.
- 2026-10-28 — Deploy fix 2: web Dockerfile no longer copies a
  non-existent `public/` directory (build failed at that COPY step).
- 2026-10-28 — Deploy fix 3: API entrypoint now runs via `sh` —
  GitHub push_files does not preserve the executable bit, so
  `entrypoint.sh` arrived non-executable on Sirius and the API
  container failed with permission denied.
- 2026-10-28 — Slice 1 LIVE on Sirius (commit `041a88f`):
  `http://100.71.239.88:8100` via Tailscale only (no 0.0.0.0 bind;
  API and DB internal only). Compose: `/opt/sirius/compose/harlearn`,
  `docker compose up -d --build`. Verified on production:
  Alembic 0001 on real PostgreSQL (`sessions`, `settings`,
  `alembic_version`), hash in container is single-`$` Argon2,
  `/gate` 200, `/` without cookie 307 to `/gate`, login 200
  (`owner: solo`), `/me` 200, dashboard with cookie 200, CSRF
  issued, logout 200, `/me` after logout 401. Note: changing the
  app password still requires editing `.env` on Sirius + restart
  (in-app password change is a later phase, not slice 1).
- 2026-10-28 — User visual confirmation (screenshot): Graphite Volt
  dashboard renders correctly on his device and the Lock button
  works. Slice 1 is closed from the user's side.
- 2026-10-28 — Fase 2 LIVE on Sirius (commit `5bfbee4`):
  canvas node minimal + save graph + run + perbandingan, provider
  DI DALAM node Model (no separate connection page, per user
  correction). Deploy fixes: compose now passes
  `HARLEARN_FERNET_KEY` to the API (missing in the first phase-2
  build); Sirius `.env` gained `HARLEARN_FERNET_KEY` (never in repo,
  never rotate casually — rotating it orphans stored Model keys).
  Verified on production: Alembic 0002 on real PostgreSQL (9 tables),
  `/graph`, `/history`, `/perbandingan` 307 without cookie, graph
  CRUD with Model key masked (`api_key` empty, `api_key_set` true)
  and the test graph deleted afterwards. NOT yet verified: a real
  LLM run against a real provider from Sirius (needs the user's own
  provider key in a Model node) and visual inspection of the new
  canvas by the user.

## Fase 2 (built locally 2026-10-28; NOT pushed, NOT deployed)

Node canvas (drag, right-click Add Node + node menu, inspector,
ports) + Model nodes carrying their own provider settings + Save Graph
+ Run from a frozen GraphVersion + History (frozen snapshot + per-node
trace) + Perbandingan 2 run (graph diff + outputs + metrics) +
Experiments (hypothesis + runs + rubric scores + conclusion notes).
Backend: FastAPI + Alembic 0002 (`graphs`, `graph_versions`, `runs`,
`experiments`, `experiment_runs`, `rubric_scores`). Model api_keys are
Fernet-encrypted in the DB and masked in the API; the `/models` fetch
endpoint is transient and stores nothing. See ARCHITECTURE.md for the
verified test results and for what was NOT verified locally (no Docker,
no PostgreSQL here — migration 0002 verified on SQLite only; no
external provider was reachable from the build VM — LLM runs were
verified against a local fake OpenAI-compatible server).

Correction applied during phase 2 (user instruction, 2026-10-28):
an earlier draft of phase 2 had a SEPARATE provider-connection entity
and a Koneksi page. That was CANCELLED before any of it was built
into a migration or route: provider settings live inside the Model
node only, and the phase-2 sidebar is Dashboard, Graph, History,
Perbandingan, Benchmark (Segera hadir). The cancelled design must not
be reintroduced without a new explicit user decision.

## Phase plan (in order, do not skip)

1. ~~Slice 1: gate + dashboard~~ (live on Sirius)
2. ~~Fase 2: node canvas + Model-node providers + frozen runs + comparisons + experiments~~ (local build; push + deploy are a separate step)
3. Canvas lanjutan + preset graph template (mis. gaya Hermes, sebagai
   snapshot graph, bukan live link) + custom node types.
4. Benchmark battery (same tasks, temperature 0, cost/latency table).
5. Agent loop: tools/MCP with an allowlist and a sandbox. Last, not first.

## Rules for this repo

- Never commit `.env`, secrets, Tailscale IPs, domains, or passwords.
- Never claim a feature that is not implemented. Sidebar items for
  future phases stay disabled and labelled until their phase lands.
- Every migration must be tested with `alembic upgrade head` from an
  empty database before deploy (lesson from Lifunze).
- Every behaviour change to an AI must be named by harness layer.
