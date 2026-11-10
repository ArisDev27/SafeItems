from django.urls import path
from . import views

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('reportar-perdido/', views.reportar_perdido, name='reportar_perdido'), # Nueva ruta
]