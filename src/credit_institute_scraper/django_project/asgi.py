import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.credit_institute_scraper.django_project.settings')
application = get_asgi_application()
