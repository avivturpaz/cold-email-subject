"""QuickBooks Online OAuth2 integration."""

import json
import urllib.request

from .base_oauth import authorization_url, exchange_code

AUTH_URL = "https://appcenter.intuit.com/connect/oauth2"
TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
SCOPE = "com.intuit.quickbooks.accounting"
API_BASE = "https://quickbooks.api.intuit.com/v3/company"


def get_auth_url(client_id: str, redirect_uri: str) -> str:
    return authorization_url(client_id, redirect_uri, SCOPE, AUTH_URL)


def get_tokens(code: str, client_id: str, client_secret: str, redirect_uri: str) -> dict:
    return exchange_code(code, client_id, client_secret, redirect_uri, TOKEN_URL)


def get_company_info(access_token: str, realm_id: str) -> dict:
    url = f"{API_BASE}/{realm_id}/companyinfo/{realm_id}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {access_token}")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}
