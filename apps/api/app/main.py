"""Harlearn API, slice 1: single-password gate + dashboard auth only.

Endpoints:
  GET  /health             - liveness, no auth
  POST /api/auth/login     - {password} -> session cookie (rate limited)
  GET  /api/auth/me        - 200 when a valid session cookie is present
  GET  /api/auth/csrf      - CSRF token for the current session
  POST /api/auth/logout    - requires session cookie + X-CSRF-Token, revokes

There is no registration, no users table, and no provider/LLM code in
slice 1. See ARCHITECTURE.md for what is planned but NOT implemented.
"""

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session as DbSession

from . import auth, config, security
from .db import get_db

app = FastAPI(title="Harlearn API", version="0.1.0-slice1")

# CORS is deliberately NOT a wildcard: only the web origin from env.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.WEB_ORIGIN],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)


class LoginBody(BaseModel):
    password: str


def _client_ip(request: Request) -> str:
    # Compose runs a single trusted reverse path (web -> api on the
    # internal network); X-Forwarded-For is NOT trusted here.
    return request.client.host if request.client else "unknown"


def _require_session(request: Request, db: DbSession):
    raw = request.cookies.get(config.COOKIE_NAME)
    row = auth.load_session(db, raw) if raw else None
    if row is None:
        raise HTTPException(status_code=401, detail="unauthenticated")
    return row


def _set_session_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        key=config.COOKIE_NAME,
        value=raw_token,
        httponly=True,
        secure=config.COOKIE_SECURE,
        samesite="lax",
        path="/",
        max_age=config.SESSION_TTL_DAYS * 24 * 3600,
    )


@app.get("/health")
def health():
    return {"status": "ok", "slice": 1}


@app.post("/api/auth/login")
def login(body: LoginBody, request: Request, response: Response, db: DbSession = Depends(get_db)):
    if not config.APP_PASSWORD_HASH:
        raise HTTPException(status_code=503, detail="app password not configured")
    ip = _client_ip(request)
    if not security.login_allowed(ip):
        raise HTTPException(status_code=429, detail="too many login attempts")
    security.record_login_attempt(ip)
    if not security.verify_app_password(body.password):
        raise HTTPException(status_code=401, detail="invalid password")
    raw_token, _row = auth.create_session(db)
    _set_session_cookie(response, raw_token)
    return {"authenticated": True, "owner": "solo"}


@app.get("/api/auth/me")
def me(request: Request, db: DbSession = Depends(get_db)):
    _require_session(request, db)
    return {"authenticated": True, "owner": "solo"}


@app.get("/api/auth/csrf")
def csrf(request: Request, db: DbSession = Depends(get_db)):
    row = _require_session(request, db)
    return {"csrf_token": row.csrf_token}


@app.post("/api/auth/logout")
def logout(request: Request, response: Response, db: DbSession = Depends(get_db)):
    row = _require_session(request, db)
    csrf_header = request.headers.get("X-CSRF-Token", "")
    if not csrf_header or csrf_header != row.csrf_token:
        raise HTTPException(status_code=403, detail="invalid csrf token")
    auth.revoke_session(db, request.cookies.get(config.COOKIE_NAME))
    response.delete_cookie(key=config.COOKIE_NAME, path="/")
    return {"authenticated": False}
