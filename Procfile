web: gunicorn app:server --preload --worker-class gevent --workers 1 --max-requests 500
scrape: python scraper.py