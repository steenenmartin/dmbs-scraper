web: gunicorn app:server --bind 0.0.0.0:${PORT:-8000} --preload --worker-class gevent --workers ${WEB_CONCURRENCY:-1} --max-requests 500 --timeout 120
worker: python -u scraper.py
