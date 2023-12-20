web: gunicorn app:server --preload --worker-class gthread --workers 1 --threads 5 --max-requests 100
scrape: python scraper.py