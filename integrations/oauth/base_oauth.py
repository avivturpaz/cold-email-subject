"""Shared OAuth2 logic — authorization, token exchange, refresh, persistence."""

import json
import sqlite3
import urllib.parse
import urllib.request


def authorization_url(client_id: str, redirect_uri: str, scope: str, auth_endpoint: str) -> str:
    params = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
    })
    return f"{auth_endpoint}?{params}"


def exchange_code(code: str, client_id: str, client_secret: str, redirect_uri: str, token_endpoint: str) -> dict:
    data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
    }).encode()
    req = urllib.request.Request(token_endpoint, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}


def refresh_token(refresh_tok: str, client_id: str, client_secret: str, token_endpoint: str) -> dict:
    data = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh_tok,
        "client_id": client_id,
        "client_secret": client_secret,
    }).encode()
    req = urllib.request.Request(token_endpoint, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}


def save_tokens(user_id: str, service: str, tokens: dict, db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS oauth_tokens (
                user_id TEXT NOT NULL,
                service TEXT NOT NULL,
                tokens TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, service)
            )
        """)
        conn.execute(
            "INSERT OR REPLACE INTO oauth_tokens (user_id, service, tokens, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
            (user_id, service, json.dumps(tokens)),
        )
        conn.commit()
    finally:
        conn.close()


def load_tokens(user_id: str, service: str, db_path: str) -> dict | None:
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT tokens FROM oauth_tokens WHERE user_id = ? AND service = ?",
            (user_id, service),
        ).fetchone()
    finally:
        conn.close()
    return json.loads(row[0]) if row else None
