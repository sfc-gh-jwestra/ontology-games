"""Snowflake OAuth (authorization code + PKCE) for the local app.

Sessions live in memory, keyed by an HttpOnly cookie, so a backend restart signs everyone out.
The role picked at sign-in becomes the session role through the scope `session:role:<ROLE>`.
"""
import base64
import hashlib
import json
import os
import re
import secrets
import subprocess
import threading
import time
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from sf import Credential, base_url

COOKIE = "oc_session"
REFRESH_MARGIN_SECS = 60
PENDING_TTL_SECS = 600

router = APIRouter()


def _roles() -> list[str]:
    return [r.strip().upper() for r in os.getenv("APP_ROLES", "").split(",") if r.strip()]


def default_role() -> str:
    role = os.getenv("APP_DEFAULT_ROLE", "").strip().upper()
    roles = _roles()
    if not roles:
        raise RuntimeError("APP_ROLES is empty; set it in backend/.env")
    if role and role not in roles:
        raise RuntimeError(f"APP_DEFAULT_ROLE {role} is not in APP_ROLES {roles}")
    return role or roles[0]


@dataclass
class Session:
    access_token: str
    refresh_token: str | None
    expires_at: float
    user: str
    role: str
    lock: threading.Lock


SESSIONS: dict[str, Session] = {}
PENDING: dict[str, tuple[str, str, float]] = {}  # state -> (code_verifier, role, created)


_CLIENT: tuple[str, str] | None = None
_CLIENT_LOCK = threading.Lock()


def _client_auth() -> tuple[str, str]:
    """OAuth client ID and secret: from .env if set, else read once from the integration.

    The lookup runs `snow sql` with a connections.toml profile whose role owns the integration
    (e.g. ACCOUNTADMIN). The snow CLI handles the profile's authenticator (including browser
    OAuth), which the pinned Python connector doesn't. The secret stays in memory only.
    """
    global _CLIENT
    if os.getenv("OAUTH_CLIENT_ID") and os.getenv("OAUTH_CLIENT_SECRET"):
        return os.environ["OAUTH_CLIENT_ID"], os.environ["OAUTH_CLIENT_SECRET"]
    with _CLIENT_LOCK:
        if _CLIENT is None:
            integration = os.getenv("OAUTH_INTEGRATION", "ONTOLOGY_COMPARE_LOCAL_OAUTH")
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", integration):
                raise RuntimeError(f"OAUTH_INTEGRATION {integration!r} is not a plain identifier")
            cmd = ["snow", "sql", "-c", os.getenv("OAUTH_SECRETS_CONNECTION", "JWESTRA_AWS1"),
                   "--role", os.getenv("OAUTH_SECRETS_ROLE", "ACCOUNTADMIN"), "--format", "json",
                   "-q", f"SELECT SYSTEM$SHOW_OAUTH_CLIENT_SECRETS('{integration}') AS S"]
            try:
                out = subprocess.run(cmd, capture_output=True, text=True, timeout=180, check=True).stdout
            except FileNotFoundError:
                raise RuntimeError("snow CLI not found; install it or set OAUTH_CLIENT_ID/OAUTH_CLIENT_SECRET in .env")
            except subprocess.CalledProcessError as exc:
                raise RuntimeError(f"snow sql failed reading OAuth client secrets: {(exc.stderr or exc.stdout)[-800:]}")
            rows = json.loads(out)
            secrets_json = json.loads(rows[0]["S"])
            _CLIENT = (secrets_json["OAUTH_CLIENT_ID"], secrets_json["OAUTH_CLIENT_SECRET"])
    return _CLIENT


def _token_request(data: dict) -> dict:
    r = httpx.post(f"{base_url()}/oauth/token-request", data=data, auth=_client_auth(), timeout=30)
    if r.status_code != 200:
        raise PermissionError(f"token request failed: HTTP {r.status_code} {r.text[:500]}")
    return r.json()


def _role_from_scope(scope: str, fallback: str) -> str:
    for part in (scope or "").split():
        if part.lower().startswith("session:role:"):
            return part.split(":", 2)[2].upper()
    return fallback


@router.get("/api/roles")
def roles():
    return {"roles": _roles(), "default": default_role()}


@router.get("/oauth/login")
def login(role: str | None = None):
    role = (role or default_role()).upper()
    if role not in _roles():
        raise HTTPException(400, f"role {role} is not in APP_ROLES")
    now = time.time()
    for s, (_, _, created) in list(PENDING.items()):
        if now - created > PENDING_TTL_SECS:
            PENDING.pop(s, None)
    state = secrets.token_urlsafe(24)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    PENDING[state] = (verifier, role, now)
    try:
        client_id = _client_auth()[0]
    except RuntimeError as exc:
        raise HTTPException(500, f"Could not get the OAuth client: {exc}")
    query = urlencode({
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": os.environ["OAUTH_REDIRECT_URI"],
        "scope": f"refresh_token session:role:{role}",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    })
    return RedirectResponse(f"{base_url()}/oauth/authorize?{query}")


@router.get("/oauth/callback")
def callback(request: Request, code: str | None = None, state: str | None = None, error: str | None = None,
             error_description: str | None = None):
    if error:
        raise HTTPException(400, f"Snowflake sign-in failed: {error} {error_description or ''}".strip())
    pending = PENDING.pop(state or "", None)
    if not code or not pending:
        raise HTTPException(400, "invalid or expired sign-in state; start again at /oauth/login")
    verifier, role, _ = pending
    try:
        tok = _token_request({
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": os.environ["OAUTH_REDIRECT_URI"],
            "code_verifier": verifier,
        })
    except PermissionError as exc:
        raise HTTPException(401, str(exc))
    sid = secrets.token_urlsafe(32)
    SESSIONS[sid] = Session(
        access_token=tok["access_token"],
        refresh_token=tok.get("refresh_token"),
        expires_at=time.time() + int(tok.get("expires_in", 600)),
        user=tok.get("username", ""),
        role=_role_from_scope(tok.get("scope", ""), role),
        lock=threading.Lock(),
    )
    old = request.cookies.get(COOKIE)
    if old:
        SESSIONS.pop(old, None)
    resp = RedirectResponse(os.getenv("APP_URL", "/"))
    resp.set_cookie(COOKIE, sid, httponly=True, samesite="lax", path="/")
    return resp


@router.post("/oauth/logout")
def logout(request: Request):
    SESSIONS.pop(request.cookies.get(COOKIE, ""), None)
    resp = RedirectResponse(os.getenv("APP_URL", "/"), status_code=303)
    resp.delete_cookie(COOKIE, path="/")
    return resp


def session_for(request: Request) -> Session:
    s = SESSIONS.get(request.cookies.get(COOKIE, ""))
    if not s:
        raise PermissionError("not signed in")
    return s


def credential(request: Request) -> Credential:
    """A valid OAuth credential for the signed-in user, refreshed when close to expiry."""
    s = session_for(request)
    with s.lock:  # both agent streams and the judge can ask at once; refresh only once
        if time.time() > s.expires_at - REFRESH_MARGIN_SECS:
            if not s.refresh_token:
                raise PermissionError("session expired; sign in again")
            tok = _token_request({"grant_type": "refresh_token", "refresh_token": s.refresh_token})
            s.access_token = tok["access_token"]
            s.refresh_token = tok.get("refresh_token", s.refresh_token)
            s.expires_at = time.time() + int(tok.get("expires_in", 600))
        return Credential(s.access_token, "OAUTH", True)
