"""Shopify OAuth2 integration."""

import json
import urllib.parse
import urllib.request


def get_auth_url(shop: str, client_id: str, redirect_uri: str, scopes: str) -> str:
    params = urllib.parse.urlencode({
        "client_id": client_id,
        "scope": scopes,
        "redirect_uri": redirect_uri,
        "response_type": "code",
    })
    return f"https://{shop}/admin/oauth/authorize?{params}"


def get_tokens(shop: str, code: str, client_id: str, client_secret: str) -> dict:
    url = f"https://{shop}/admin/oauth/access_token"
    data = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
    }).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}


def get_products(shop: str, access_token: str, limit: int = 10) -> list:
    url = f"https://{shop}/admin/api/2024-01/products.json?limit={limit}"
    req = urllib.request.Request(url)
    req.add_header("X-Shopify-Access-Token", access_token)
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        return data.get("products", [])
    except Exception as e:
        return [{"error": str(e)}]
