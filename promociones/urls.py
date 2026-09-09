from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('', views.promociones, name='promociones'),
    # Suscripci�n inicial con primera promoci�n
    path('promociones/suscribir/', views.suscribir_promocion, name='suscribir_promocion'),
    
    # Crear promoci�n adicional (requiere suscripci�n activa)
    path('promociones/crear-adicional/', views.crear_promocion_adicional, name='crear_promocion_adicional'),
    
    # Alias para compatibilidad
    path('promociones/crear/', views.crear_promocion_adicional, name='crear_promocion'),
    
    # Mis promociones
    path('p/<str:slug>/', views.promotion_public, name='ver_promocion'),

    path('promociones/mis-promociones/', views.mis_promociones, name='mis_promociones'),

    path('dashboard/', views.dashboard, name='dashboard'),
    path('create/step1/', views.create_promotion_step1, name='create_step1'),
    path('create/step2/', views.create_promotion_step2, name='create_step2'),
    path('edit/<int:pk>/', views.edit_promotion, name='edit'),
]





