#!/usr/bin/env bash
set -euo pipefail

# Niteshift setup script for flask-examples
# This script sets up the Python environment and dependencies for running Flask example applications.

# Logging setup
if [ -n "${NITESHIFT_LOG_FILE:-}" ]; then
    exec > >(tee -a "$NITESHIFT_LOG_FILE") 2>&1
fi

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

log "Starting setup for flask-examples..."

# Detect Python command
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    log "ERROR: Python is not installed. Please install Python 3.6+ to continue."
    exit 1
fi

log "Using Python command: $PYTHON_CMD"
$PYTHON_CMD --version

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    log "Creating virtual environment..."
    $PYTHON_CMD -m venv venv
    log "Virtual environment created."
else
    log "Virtual environment already exists."
fi

# Activate virtual environment
log "Activating virtual environment..."
# shellcheck disable=SC1091
source venv/bin/activate

# Upgrade pip to avoid potential issues
log "Upgrading pip..."
pip install --upgrade pip -q

# Install dependencies
if [ -f "requirements.txt" ]; then
    log "Installing Python dependencies from requirements.txt..."
    pip install -r requirements.txt -q
    log "Dependencies installed successfully."
else
    log "WARNING: requirements.txt not found. Skipping dependency installation."
fi

# Initialize database for database example
log "Initializing database for database example..."
cd database
if [ ! -f "data.db" ]; then
    log "Creating database..."
    FLASK_APP=app.py flask initdb
    log "Database initialized."
else
    log "Database already exists. Skipping initialization."
fi
cd ..

log "Setup complete!"
log ""
log "To run an example application:"
log "  1. Activate the virtual environment: source venv/bin/activate"
log "  2. Navigate to an example directory: cd hello"
log "  3. Run the Flask app: flask run"
log ""
log "Available examples: hello, http, template, form, database, email, assets, cache"