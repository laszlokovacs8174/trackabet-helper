"""Import bets from the live Track-A-Bet API into the local database.

Usage:
    python -m trackabet.import_from_trackabet <response.json>
    
Or with a session cookie:
    curl -s -H "Cookie: session=..." https://trackabet.bettingiscool.com/api/bets > bets.json
    python -m trackabet.import_from_trackabet bets.json
"""
import json
import sys
from pathlib import Path

from . import database as db


def import_bets(json_file: str):
    """Import bets from a Track-A-Bet API JSON response into the local DB."""
    db.init_db()
    
    raw = json.loads(Path(json_file).read_text())
    
    if isinstance(raw, dict) and "bets" in raw:
        bets = raw["bets"]
    elif isinstance(raw, list):
        bets = raw
    else:
        print(f"❌ Unexpected JSON structure. Got {type(raw).__name__}")
        return
    
    print(f"📥 Found {len(bets)} bets to import...")
    
    imported = 0
    skipped = 0
    
    for bet in bets:
        # Map Track-A-Bet fields to our local schema
        trackabet_id = str(bet["id"])
        
        # Build event name from runner names
        home = bet.get("runner_home") or ""
        away = bet.get("runner_away") or ""
        if home and away:
            event = f"{home} vs {away}"
        elif home:
            event = home
        elif away:
            event = away
        else:
            event = bet.get("special_name") or f"Event #{bet['event_id']}"
        
        # Add league name if available
        league = bet.get("league_name")
        if league:
            event = f"{event} ({league})"
        
        # Map sport
        sport = (bet.get("sport_name") or "other").lower().replace(" ", "-")
        
        # Build selection description
        selection = bet.get("selection") or ""
        handicap = bet.get("handicap")
        if handicap is not None:
            selection = f"{selection} ({handicap:+.1f})"
        
        # Add line info
        line = bet.get("line")
        if line and "over" not in selection.lower() and "under" not in selection.lower():
            selection = f"{selection} ({line})"
        
        # Determine status from profit
        profit = bet.get("profit")
        
        if profit is None:
            status = "pending"
        elif profit > 0:
            status = "won"
        elif profit == 0:
            status = "push"
        else:  # profit < 0
            status = "lost"
        
        # Map market type
        market_type = bet.get("market", "moneyline")
        
        # Tag/tipster
        tag = bet.get("tag") or ""
        
        local_bet = {
            "event": event,
            "sport": sport,
            "market_type": market_type,
            "selection": selection,
            "odds": bet["bet_price"],
            "stake": bet["bet_stake"],
            "bookmaker": tag.lower() if tag else "other",
            "tipster": tag,
            "notes": "",
            "status": status,
            "profit": profit if profit is not None else 0,
            "clv": bet.get("clv", 0),
            "trackabet_id": trackabet_id,
            "created_at": bet.get("created_at", ""),
        }
        
        db.add_bet(local_bet)
        imported += 1
    
    print(f"✅ Imported: {imported} new bets")
    print(f"⏭️  Skipped (already exist): {skipped}")
    print(f"📊 Total in local DB: {imported + skipped}")
    
    # Show summary stats
    stats = db.get_stats()
    print(f"\n📈 Local stats:")
    print(f"   Total: {stats['total_bets']}")
    print(f"   Won:   {stats['wins']}")
    print(f"   Lost:  {stats['losses']}")
    print(f"   Pending: {stats['pending']}")
    print(f"   P/L:   ${stats['total_profit']:.2f}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m trackabet.import_from_trackabet <bets.json>")
        sys.exit(1)
    import_bets(sys.argv[1])
