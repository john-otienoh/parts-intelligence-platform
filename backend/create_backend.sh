#!/bin/bash
# ============================================================
# BE FORWARD Backend — Project Scaffolder
# Run: bash create_backend.sh
# ============================================================

set -e

PROJECT_DIR="${1:-.}"
echo "Scaffolding FastAPI backend in: $PROJECT_DIR"

mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# Core app structure
mkdir -p app/{models,schemas,routers,services,core,tasks}
mkdir -p migrations/versions
mkdir -p tests/{unit,integration}

# Empty __init__.py files
touch app/__init__.py
touch app/models/__init__.py
touch app/schemas/__init__.py
touch app/routers/__init__.py
touch app/services/__init__.py
touch app/core/__init__.py
touch app/tasks/__init__.py
touch tests/__init__.py
touch tests/unit/__init__.py
touch tests/integration/__init__.py

echo ""
echo "✅ Backend scaffolded successfully in: $(pwd)"
echo ""