#!/bin/bash
# Track-A-Bet TabHelper - Convenience launcher
# Add to your PATH or alias: alias tabhelper="cd /path/to/trackabet-helper && python run.py"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ $# -eq 0 ]; then
    python run.py web
else
    python run.py "$@"
fi
