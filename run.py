#!/usr/bin/env python3
"""Track-A-Bet TabHelper - Entry point.

Usage:
    python run.py web            # Start web dashboard
    python run.py log <bet>      # Log a bet (CLI)
    python run.py list           # View recent bets
    python run.py stats          # View stats
    python run.py --help         # Full help
"""
import sys
import os

# Ensure the package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from trackabet.cli import cli

if __name__ == "__main__":
    cli()
