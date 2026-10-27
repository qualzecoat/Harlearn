# Harlearn — Project context

> This file is the AI context for the repo. Update it on every locked
> decision, exactly like PROJECT.md in the Lifunze repo.

## What Harlearn is

A solo AI lab for learning harnesses by direct comparison, and later for
benchmarking models/providers. The user learns best by seeing two runs
side by side when exactly one thing changes — not by reading definitions.

Core workflow (target, not slice 1):
1. Connect an OpenAI-compatible provider (base URL + API key + model).
2. Assemble a harness from layers: soul, system prompt, memory, user
   profile, skills, tools/MCP, output schema/parser.
3. Or load a preset from an agent (e.g. Hermes) — as a *snapshot* into a
   Harlearn profile, never as a live link to that agent's home directory.
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
- **Lab shape (future):** node-style canvas like n8n/ComfyUI. Canvas =
  recipe (graph); Run = execution of a frozen graph version; Experiment =
  a set of runs + rubric. Recording lives in History/Experiments, not
  inside the canvas. Custom nodes are planned for later, not slice 1.
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

## Phase plan (in order, do not skip)

1. ~~Slice 1: gate + dashboard~~ (local build; deploy is a separate step)
2. Provider connections (OpenAI-compatible, Fernet-encrypted keys, masked
   display, `/models` fetch, mini connection test) — pattern already
   proven in Rephore/Lifunze.
3. Harness profiles + node canvas (linear assembly first; DAG data model
   from the start) + Run recording + History.
4. Experiments & comparisons (run diffs, rubric scores).
5. Benchmark battery (same tasks, temperature 0, cost/latency table).
6. Agent loop: tools/MCP with an allowlist and a sandbox. Last, not first.

## Rules for this repo

- Never commit `.env`, secrets, Tailscale IPs, domains, or passwords.
- Never claim a feature that is not implemented. Sidebar items for
  future phases stay disabled and labelled until their phase lands.
- Every migration must be tested with `alembic upgrade head` from an
  empty database before deploy (lesson from Lifunze).
- Every behaviour change to an AI must be named by harness layer.
