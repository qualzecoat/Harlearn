"""Slice 1 auth contract tests (run with pytest from apps/api)."""


def test_health():
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as c:
        assert c.get("/health").status_code == 200


def test_login_success_and_me(client):
    r = client.post("/api/auth/login", json={"password": "test-password"})
    assert r.status_code == 200, r.text
    assert "harlearn_session" in r.cookies
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["owner"] == "solo"


def test_login_wrong_password_401(client):
    r = client.post("/api/auth/login", json={"password": "wrong"})
    assert r.status_code == 401
    assert client.get("/api/auth/me").status_code == 401


def test_me_without_cookie_401(client):
    assert client.get("/api/auth/me").status_code == 401


def test_csrf_required_for_logout(authed_client):
    # Logout without the CSRF header must fail and must NOT revoke.
    assert authed_client.post("/api/auth/logout").status_code == 403
    assert authed_client.get("/api/auth/me").status_code == 200


def test_logout_revokes_session(authed_client):
    csrf = authed_client.get("/api/auth/csrf").json()["csrf_token"]
    r = authed_client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf})
    assert r.status_code == 200
    # The old cookie must no longer authenticate, even if replayed.
    assert authed_client.get("/api/auth/me").status_code == 401
