from django.urls import path, include

urlpatterns = [
    path('', include('src.credit_institute_scraper.web.urls')),
]
