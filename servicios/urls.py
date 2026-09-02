from django.urls import path
from . import views

urlpatterns = [
    path('servicios/<slug:slug>/', views.detalle_servicio, name='detalle_servicio'),
    #path('servicios/', views.servicios, name='servicios'),
    path('suscribirse/<int:plan_id>/', views.procesar_suscripcion, name='procesar_suscripcion'),
    # Agregar rutas similares para otros productos...
]