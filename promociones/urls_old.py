from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve
from django.conf import settings
from django.conf.urls.static import static
from . import views

"""urlpatterns = [
    path('', views.promociones, name='promociones'),
    
    
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
]"""

# promociones/urls.py
from django.urls import path
from . import views

app_name = 'promociones'

urlpatterns = [
    # ---- Cliente ----
    # Suscripcion inicial con primera promocion
    path('promociones/suscribir/', views.suscribir_promocion, name='suscribir_promocion'),
    path('mis-promociones/', views.mis_promociones, name='mis_promociones'),
    path('crear/', views.crear_promocion, name='crear'),
    path('crear/plantilla/<int:template_id>/', views.crear_desde_plantilla, name='crear_desde_plantilla'),
    path('crear/imagen/', views.crear_con_imagen, name='crear_con_imagen'),
    path('crear/ia/', views.crear_con_ia, name='crear_con_ia'),
    path('solicitud/<int:pk>/', views.detalle_solicitud_cliente, name='detalle_solicitud'),
    path('solicitud/<int:pk>/aprobar/', views.cliente_aprobar_diseno, name='cliente_aprobar'),
    path('solicitud/<int:pk>/solicitar-cambios/', views.cliente_solicitar_cambios, name='cliente_solicitar_cambios'),

    # ---- Admin / Cobosis ----
    path('panel/', views.panel_promociones, name='panel_promociones'),
    path('panel/<int:pk>/', views.admin_detalle_solicitud, name='admin_detalle_solicitud'),
    path('panel/<int:pk>/estado/<str:nuevo_estado>/', views.admin_cambiar_estado, name='admin_cambiar_estado'),
    path('panel/<int:pk>/subir-diseno/', views.admin_subir_diseno, name='admin_subir_diseno'),
]