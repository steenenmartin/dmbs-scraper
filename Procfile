web: gunicorn app:server --preload --worker-class gevent --workers 1 --max-requests 100
scrape: python scraper.py