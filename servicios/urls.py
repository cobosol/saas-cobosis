from django.urls import path
from . import views

urlpatterns = [
    path('<slug:slug>/', views.detalle_servicio, name='detalle_servicio'),
    # Agregar rutas similares para otros productos...
]