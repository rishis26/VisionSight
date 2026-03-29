#!/bin/bash

# run_daemon.sh - Executed by launchd to run the python daemon

# Navigate to the project directory
cd /Users/rishishah/Study/Project/VisionSight || exit 1

# Export PYTHONPATH so the modules load properly
export PYTHONPATH="/Users/rishishah/Study/Project/VisionSight:$PYTHONPATH"

# Force Python to flush stdout/stderr immediately so we can see logs
export PYTHONUNBUFFERED=1

# Execute Python via the virtual environment directly.
# "exec" replaces the shell with python so launchd tracks the python PID directly.
# Using -u to ensure the output is completely unbuffered
exec /Users/rishishah/Study/Project/VisionSight/venv/bin/python -u main.py
