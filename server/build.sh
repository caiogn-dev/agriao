#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install dependencies
pip3 install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput

# Apply database migrations

python manage.py makemigrations
python manage.py migrate

python scripts/create_marmitas.py