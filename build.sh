#!/usr/bin/env bash
# Build script para Render
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --no-input
