"""Natural language bet string parser.

Parses strings like:
  "Man Utd -1.5 @ 2.10 $50"
  "Arsenal vs Chelsea over 2.5 goals @ 1.85 $100"
  "Federer @ 2.20 $50" (moneyline)
  "Lakers -5.5 vs Celtics @ 1.95 $75"
"""
import re
from typing import Optional


def parse_bet_string(text: str) -> Optional[dict]:
    """
    Attempt to parse a natural language bet string into structured fields.
    Returns None if parsing fails.
    """
    text = text.strip()
    if not text:
        return None

    result = {"event": "", "selection": "", "odds": 0.0, "stake": 0.0}

    # Pattern: <event/selection> @ <odds> $<stake>
    # or:       <event/selection> @ <odds> <stake> (unit assumed)
    patterns = [
        # "Team A -1.5 @ 2.10 $50" or "Team A @ 2.10 $50"
        r"^(.+?)\s+@\s+(\d+\.?\d*)\s+\$?(\d+\.?\d*)$",
        # "Team A vs Team B over 2.5 @ 1.85 $100"
        r"^(.+?)\s+@\s+(\d+\.?\d*)\s+\$?(\d+\.?\d*)\s*$",
    ]

    for pat in patterns:
        m = re.match(pat, text, re.IGNORECASE)
        if m:
            selection_raw = m.group(1).strip()
            result["odds"] = float(m.group(2))
            result["stake"] = float(m.group(3))

            # Try to detect if this contains a handicap/line
            # e.g. "Man Utd -1.5" or "Over 2.5 Goals"
            result["selection"] = selection_raw

            # Use selection as event name too (user can refine)
            result["event"] = selection_raw
            return result

    # Try simpler: just "Team @ odds" with no stake
    m = re.match(r"^(.+?)\s+@\s+(\d+\.?\d*)$", text, re.IGNORECASE)
    if m:
        result["selection"] = m.group(1).strip()
        result["event"] = result["selection"]
        result["odds"] = float(m.group(2))
        result["stake"] = 0.0
        return result

    return None


def parse_cli_args(event: str, **kwargs) -> dict:
    """Build a clean bet dict from CLI args, with smart defaults."""
    bet = {
        "event": event,
        "sport": kwargs.get("sport", "other"),
        "market_type": kwargs.get("market_type", "moneyline"),
        "selection": kwargs.get("selection", event),
        "odds": kwargs.get("odds", 0.0),
        "stake": kwargs.get("stake", 0.0),
        "bookmaker": kwargs.get("bookmaker", "bet365"),
        "tipster": kwargs.get("tipster", ""),
        "notes": kwargs.get("notes", ""),
    }
    return bet
