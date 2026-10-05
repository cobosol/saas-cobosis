"""
Rutas de la aplicación 'promociones'.

Todas las vistas del cliente viven bajo el namespace 'promociones'
(app_name), por ejemplo: {% url 'promociones:crear_promocion' %}.

Incluir en el urls.py del proyecto (saas/urls.py):

    urlpatterns = [
        ...
        path('promociones/', include('promociones.urls')),
    ]
"""
from django.urls import path

from . import views

app_name = 'promociones'

urlpatterns = [
    # ------------------------- Cliente -------------------------
    path('', views.promociones, name='promociones'),
    path('panel/', views.mis_promociones, name='panel_promociones'),  # alias usado por servicios
    path('suscribir/<int:plan_id>/', views.suscribir_promocion, name='suscribir_promocion'),
    path('primera-promocion/<int:plan_id>/', views.primera_promocion, name='primera_promocion'),
    path('crear/', views.crear_promocion, name='crear_promocion'),
    path('solicitud/<int:solicitud_id>/enviada/', views.solicitud_enviada, name='solicitud_enviada'),
    path('solicitud/<int:pk>/aprobar-diseno/', views.cliente_aprobar_diseno, name='cliente_aprobar_diseno'),

    # ------------------------- Públicas -------------------------
    path('publicadas/', views.listado_publicadas, name='listado_publicadas'),
    path('p/<slug:slug>/', views.ver_promocion, name='ver_promocion'),
    
    # ------------------- Equipo administrativo -------------------
    path('gestion/solicitudes/', views.admin_solicitudes, name='admin_solicitudes'),
    path('gestion/solicitudes/<int:pk>/', views.admin_solicitud_detalle, name='admin_solicitud_detalle'),
    path('gestion/solicitudes/<int:pk>/estado/', views.admin_cambiar_estado, name='admin_cambiar_estado'),
    path('gestion/solicitudes/<int:pk>/publicar/', views.admin_publicar_promocion, name='admin_publicar_promocion'),

    # Tarjeta: crear (borrador) -> editar -> publicar / despublicar (estados intermedios)
    path('gestion/solicitudes/<int:pk>/tarjeta/crear/', views.admin_crear_tarjeta, name='admin_crear_tarjeta'),
    path('gestion/solicitudes/<int:pk>/tarjeta/editar/', views.admin_editar_tarjeta, name='admin_editar_tarjeta'),
    path('gestion/solicitudes/<int:pk>/tarjeta/publicar/', views.admin_publicar_tarjeta, name='admin_publicar_tarjeta'),
    path('gestion/solicitudes/<int:pk>/tarjeta/despublicar/', views.admin_despublicar_tarjeta, name='admin_despublicar_tarjeta'),
    
        # Suscripción: activar al confirmar el pago (sin esperar a la tarjeta)
    path('gestion/solicitudes/<int:pk>/suscripcion/activar/', views.admin_activar_suscripcion, name='admin_activar_suscripcion'),    
]
