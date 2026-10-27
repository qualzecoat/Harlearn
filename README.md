# Harlearn

Harlearn is a solo AI lab: connect an OpenAI-compatible provider, assemble
a harness from layers (soul, system prompt, memory, skills, tools, output
schema), run the same task under different harnesses, save every run, and
compare them. Later phases add model/provider benchmarking.

**Slice 1 scope — and only this scope:** a single-password gate plus a
dashboard shell. There is no node canvas, no provider connection, no run,
no comparison, and no benchmark yet. Sidebar items for those phases are
present in the dashboard but disabled and labelled “Segera hadir”.

Theme: **Graphite Volt** — background `#111827`, surface `#1F2937`,
accent lime `#A3E635`, secondary cyan `#22D3EE`, text `#F3F4F6`,
muted `#9CA3AF`, border `#374151`. Deliberately different from Lifunze
(violet `#6D5DF6` + amber `#FFB020`).

## Stack

- `apps/web` — Next.js 14 (App Router), standalone output
- `apps/api` — FastAPI + SQLAlchemy + Alembic
- `db` — PostgreSQL 16 (compose only; tests use SQLite)
- Monorepo, Docker Compose, Tailscale-only publishing (see below)

## Run locally (development, no Docker)

```bash
# 1. Backend
cd apps/api
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

# 2. Generate the app-password hash (password is never stored by the script)
python ../../tools/hash_password.py
# Paste the printed hash into your environment as HARLEARN_APP_PASSWORD_HASH.

# 3. Start the API (SQLite for local dev only; compose uses PostgreSQL)
DATABASE_URL="sqlite:///./dev.db" \
HARLEARN_APP_PASSWORD_HASH="<paste hash here>" \
WEB_ORIGIN="http://127.0.0.1:3000" \
uvicorn app.main:app --host 127.0.0.1 --port 8000

# 4. Start the web UI (new terminal; API_INTERNAL_URL points at the API)
cd ../web
npm install
API_INTERNAL_URL=http://127.0.0.1:8000 npm run dev
# Open http://127.0.0.1:3000 — you land on /gate. Enter the app password.
```

Run the backend tests:

```bash
cd apps/api
python -m pytest tests/ -q
```

## Run with Docker Compose (deploy-shaped)

```bash
cp .env.example .env
# Edit .env: set TAILSCALE_IP to the host's Tailscale IP and
# HARLEARN_APP_PASSWORD_HASH from tools/hash_password.py.
# NEVER commit .env, a real Tailscale IP, a domain, or any password.
docker compose up -d --build
# Web UI: http://<TAILSCALE_IP>:8100  (Tailscale only, never 0.0.0.0)
```

The API and database are **not** published: the browser calls same-origin
`/api/*` on the web service, which rewrites it to the internal `api`
service (`API_INTERNAL_URL=http://api:8000` in compose).

## Security notes (slice 1)

- Single app password, Argon2 hash from `HARLEARN_APP_PASSWORD_HASH`.
  No registration, no roles, no `users` table in this slice.
- Sessions are server-side rows in PostgreSQL; the cookie holds only a
  random token (the DB stores its SHA-256 hash). Cookie: HttpOnly,
  SameSite=Lax, 7-day expiry. Logout deletes the session row — an old
  cookie cannot be replayed (covered by test).
- Mutations after login require the per-session CSRF token
  (`GET /api/auth/csrf` → `X-CSRF-Token` header).
- Login rate limit is in-memory per process (5 attempts / 15 min / IP).
  It is temporary — see ARCHITECTURE.md before running more than one
  API replica.
- CORS allows only `WEB_ORIGIN`, never `*`.

## Docs

- `PROJECT.md` — what Harlearn is, locked decisions, phase plan
- `ARCHITECTURE.md` — architecture, data-model principles, known gaps
