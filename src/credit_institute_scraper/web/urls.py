from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('prices/', views.prices, name='prices'),
    path('rates/', views.rates, name='rates'),
    path('ohlc/', views.ohlc, name='ohlc'),
    path('export/', views.export_csv, name='export'),
]
