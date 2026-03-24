"""HubSpot OAuth2 integration."""

import json
import urllib.parse
import urllib.request

from .base_oauth import authorization_url, exchange_code

AUTH_URL = "https://app.hubspot.com/oauth/authorize"
TOKEN_URL = "https://api.hubapi.com/oauth/v1/token"
SCOPE = "contacts"
API_BASE = "https://api.hubapi.com"


def get_auth_url(client_id: str, redirect_uri: str) -> str:
    return authorization_url(client_id, redirect_uri, SCOPE, AUTH_URL)


def get_tokens(code: str, client_id: str, client_secret: str, redirect_uri: str) -> dict:
    return exchange_code(code, client_id, client_secret, redirect_uri, TOKEN_URL)


def get_contacts(access_token: str, limit: int = 10) -> list:
    url = f"{API_BASE}/crm/v3/objects/contacts?limit={limit}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {access_token}")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        return data.get("results", [])
    except Exception as e:
        return [{"error": str(e)}]
