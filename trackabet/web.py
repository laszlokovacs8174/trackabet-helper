"""Web dashboard for Track-A-Bet TabHelper.

Provides a local web UI for logging bets quickly,
with auto-detect parsing and session tracking.
"""
import json
import webbrowser
from pathlib import Path
from datetime import datetime
from typing import Optional

from flask import Flask, render_template, request, jsonify, redirect, url_for

from . import database as db
from .parser import parse_bet_string
from .config import load_config

app = Flask(__name__)

# Template path relative to this file
HERE = Path(__file__).parent
TEMPLATE_DIR = HERE / "templates"
STATIC_DIR = HERE / "static"


def create_app():
    """Create and configure the Flask app."""
    db.init_db()
    return app


@app.route("/")
def index():
    """Main dashboard page."""
    stats = db.get_stats()
    recent_bets = db.get_recent_bets(limit=10)
    email = db.get_session_email()
    config = load_config()
    return render_template(
        "index.html",
        stats=stats,
        recent_bets=recent_bets,
        email=email or "",
        bookmakers=config.get("bookmakers", []),
        sports=config.get("recent_sports", []),
    )


@app.route("/api/bets", methods=["GET"])
def api_get_bets():
    """Get bets (JSON API)."""
    limit = request.args.get("limit", 50, type=int)
    sport = request.args.get("sport")
    bets = db.get_recent_bets(limit=limit, sport=sport)
    return jsonify({"bets": bets, "count": len(bets)})


@app.route("/api/bets", methods=["POST"])
def api_add_bet():
    """Add a bet (JSON API)."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    required = ["event", "selection", "odds", "stake"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    try:
        bet_id = db.add_bet(data)
        bet = db.get_bet(bet_id)
        return jsonify({"success": True, "bet": bet, "id": bet_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/bets/<int:bet_id>", methods=["GET"])
def api_get_bet(bet_id):
    """Get a single bet."""
    bet = db.get_bet(bet_id)
    if not bet:
        return jsonify({"error": "Bet not found"}), 404
    return jsonify(bet)


@app.route("/api/bets/<int:bet_id>", methods=["PATCH"])
def api_update_bet(bet_id):
    """Update a bet."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data"}), 400
    db.update_bet(bet_id, **data)
    bet = db.get_bet(bet_id)
    return jsonify({"success": True, "bet": bet})


@app.route("/api/stats", methods=["GET"])
def api_stats():
    """Get stats."""
    stats = db.get_stats()
    return jsonify(stats)


@app.route("/api/parse", methods=["POST"])
def api_parse():
    """Parse a natural language bet string."""
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "No text provided"}), 400
    result = parse_bet_string(data["text"])
    if result:
        return jsonify({"success": True, "parsed": result})
    return jsonify({"success": False, "parsed": None})


@app.route("/api/config", methods=["GET"])
def api_get_config():
    """Get current config."""
    config = load_config()
    # Don't expose tokens
    config.pop("session_token", None)
    return jsonify(config)


@app.route("/api/email", methods=["POST"])
def api_set_email():
    """Set the Track-A-Bet email."""
    data = request.get_json()
    if not data or "email" not in data:
        return jsonify({"error": "No email provided"}), 400
    db.set_session_email(data["email"])
    return jsonify({"success": True, "email": data["email"]})


def start_server(host="127.0.0.1", port=6789):
    """Start the Flask development server."""
    create_app()
    print(f"╔══════════════════════════════════════════════╗")
    print(f"║  📊 Track-A-Bet TabHelper                     ║")
    print(f"║                                              ║")
    print(f"║  🌐 Web UI:  http://{host}:{port}                ║")
    print(f"║  ⌨️  CLI:    trackabet --help                 ║")
    print(f"║                                              ║")
    print(f"║  Press Ctrl+C to stop                        ║")
    print(f"╚══════════════════════════════════════════════╝")
    app.run(host=host, port=port, debug=False)
