from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]
SECRET_KEY = 'dmbs-scraper-dev-key'
DEBUG = True
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'src.credit_institute_scraper.web',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'src.credit_institute_scraper.django_project.urls'
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {'context_processors': []},
    },
]

WSGI_APPLICATION = 'src.credit_institute_scraper.django_project.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'd6v4equ3b5lrg3',
        'USER': 'ufat6r7kf9ccoe',
        'PASSWORD': 'pab015156b9089bb6d27b8bbc4b7ec7e693b14bac792335671b78029da29a2d32',
        'HOST': 'c35nvon35iqc30.cluster-czz5s0kz4scl.eu-west-1.rds.amazonaws.com',
        'PORT': '5432',
    }
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Europe/Copenhagen'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
