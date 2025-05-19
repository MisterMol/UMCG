#!/bin/sh

# Playwright headless browser installeren (eenmalig vereist in container)
playwright install --with-deps

# Database migraties uitvoeren
python manage.py migrate --noinput

# Static files verzamelen
python manage.py collectstatic --noinput

# Gunicorn starten
exec gunicorn umcg_project.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --threads 2 \
    --timeout 120 \
    --log-level=info
