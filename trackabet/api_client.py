"""Client for interacting with the Track-A-Bet API on trackabet.bettingiscool.com.

Since the user authenticates via email-magic-link and stays logged in via browser
cookies, this module provides:
  1. A way to log bets locally (offline-first).
  2. Manual sync to the Track-A-Bet web app (opens browser or uses requests).
  3. Parsing Session cookies from the browser for API calls.

The Track-A-Bet API is reverse-engineered from the web app's network requests.
"""
import json
import requests
from typing import Optional
from urllib.parse import urljoin

from .config import load_config


class TrackABetClient:
    """HTTP client for Track-A-Bet's internal API."""

    def __init__(self, base_url: str = "https://trackabet.bettingiscool.com",
                 session_token: str = ""):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "TrackABet-TabHelper/1.0",
            "Accept": "application/json",
        })
        if session_token:
            self.session.headers.update({
                "Authorization": f"Bearer {session_token}",
                "X-Session-Token": session_token,
            })

    def set_token(self, token: str):
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "X-Session-Token": token,
        })

    def set_cookie(self, cookie_str: str):
        """Set raw cookie string from browser session."""
        self.session.headers.update({"Cookie": cookie_str})

    def _request(self, method: str, path: str, **kwargs) -> Optional[dict]:
        url = urljoin(self.base_url, path)
        try:
            resp = self.session.request(method, url, timeout=15, **kwargs)
            if resp.status_code == 200:
                try:
                    return resp.json()
                except (json.JSONDecodeError, ValueError):
                    return {"raw": resp.text}
            elif resp.status_code == 401:
                return {"error": "unauthorized", "message": "Session expired. Please re-login."}
            elif resp.status_code == 404:
                return {"error": "not_found", "message": f"Endpoint not found: {path}"}
            else:
                return {"error": f"http_{resp.status_code}", "message": resp.text[:500]}
        except requests.RequestException as e:
            return {"error": "connection_error", "message": str(e)}

    def check_health(self) -> Optional[dict]:
        """Check if the API is reachable."""
        return self._request("GET", "/api/health")

    def get_bets(self, page: int = 1, limit: int = 50) -> Optional[dict]:
        """Get bets from Track-A-Bet."""
        return self._request("GET", "/api/bets", params={"page": page, "limit": limit})

    def add_bet(self, bet_data: dict) -> Optional[dict]:
        """Log a bet to Track-A-Bet."""
        return self._request("POST", "/api/bets", json=bet_data)

    def search_events(self, query: str) -> Optional[dict]:
        """Search for events to bet on."""
        return self._request("GET", "/api/events/search", params={"q": query})

    def get_odds(self, event_id: str) -> Optional[dict]:
        """Get odds/markets for a specific event."""
        return self._request("GET", f"/api/events/{event_id}/odds")

    def get_stats(self) -> Optional[dict]:
        """Get user betting stats."""
        return self._request("GET", "/api/stats")

    def request_login_link(self, email: str) -> Optional[dict]:
        """Request a magic login link."""
        return self._request("POST", "/api/auth/login", json={"email": email})

    def verify_session(self) -> Optional[dict]:
        """Check if current session is valid."""
        return self._request("GET", "/api/auth/me")
