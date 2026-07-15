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
                 session_token: str = "", session_cookie: str = ""):
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
        if session_cookie:
            self.session.headers.update({"Cookie": session_cookie})

    @classmethod
    def from_config(cls):
        """Create a client using saved config (cookie or token)."""
        config = load_config()
        return cls(
            base_url=config.get("api_base_url", "https://trackabet.bettingiscool.com"),
            session_token=config.get("session_token", ""),
            session_cookie=config.get("session_cookie", ""),
        )

    def set_token(self, token: str):
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "X-Session-Token": token,
        })

    def set_cookie(self, cookie_str: str):
        """Set raw cookie string from browser session."""
        self.session.headers.update({"Cookie": cookie_str})

    def _request(self, method: str, path: str, **kwargs):
        """Make an HTTP request. Returns parsed JSON or raises on failure."""
        url = urljoin(self.base_url, path)
        resp = self.session.request(method, url, timeout=30, **kwargs)
        if resp.status_code == 401:
            raise PermissionError("Session expired. Re-login to Track-A-Bet and save your cookie.")
        if resp.status_code != 200:
            raise ConnectionError(f"HTTP {resp.status_code}: {resp.text[:200]}")
        try:
            return resp.json()
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Invalid JSON response: {e}")

    def check_health(self) -> dict:
        """Check if the API is reachable."""
        return self._request("GET", "/api/health")

    def get_all_bets(self) -> list:
        """Get all bets from Track-A-Bet (returns raw array)."""
        return self._request("GET", "/api/bets")

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
