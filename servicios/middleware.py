"""
Middleware de suscripción activa (VERSIÓN CORREGIDA).

Errores de la versión anterior y cómo se resolvieron:
    1. Filtraba Suscripcion con estado='active' pero el modelo define 'activa'
       -> nadie tenía nunca una suscripción "válida" y todos eran redirigidos.
    2. Comparaba subscription.fecha_fin (DateField) con timezone.now() (datetime)
       -> TypeError en tiempo de ejecución. Ahora usa timezone.localdate().
    3. Bloqueaba TODAS las URLs para cualquier usuario autenticado sin plan
       activo, incluidas las propias páginas de suscripción/registro del flujo
       de promociones -> era imposible completar la compra de un plan.
       Ahora hay una lista de rutas exentas que incluye todo el flujo comercial.
    4. Llamaba a reverse() sobre nombres de URLs que podrían no existir y fallaba
       con NoReverseMatch. Ahora usa prefijos de ruta (más robusto).

Colócalo en settings.py (después de AuthenticationMiddleware):

    MIDDLEWARE = [
        ...
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        ...
        'servicios.middleware.ActiveSubscriptionMiddleware',
    ]
"""
from django.db.models import Q
from django.shortcuts import redirect
from django.utils import timezone

from .models import Suscripcion


class ActiveSubscriptionMiddleware:
    """Verifica que el usuario tenga una suscripción activa para usar los
    paneles de los servicios. Todo el flujo comercial (registro, detalle de
    servicios, suscripción, primera promoción, etc.) queda EXENTO para que los
    usuarios puedan contratar planes sin bloqueos."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.is_staff:
            if not self._ruta_exenta(request.path):
                tiene_acceso = Suscripcion.objects.filter(
                    usuario=request.user,
                    estado='activa',           # <- antes decía 'active' (bug)
                ).filter(
                    # fecha_fin es un DateField: comparar contra localdate()
                    Q(fecha_fin__isnull=True) | Q(fecha_fin__gte=timezone.localdate())
                ).exists()

                if not tiene_acceso:
                    print("No tiene acceso")
                    # Si alguna suscripción expiró, se marca para que el equipo
                    # lo vea en el panel de suscripciones.
                    Suscripcion.objects.filter(
                        usuario=request.user,
                        estado='activa',
                        fecha_fin__lt=timezone.localdate(),
                    ).update(estado='vencida')

                    return redirect('inicio')

        return self.get_response(request)

    @staticmethod
    def _ruta_exenta(path):
        """Rutas que NO requieren suscripción activa."""
        prefijos_exentos = (
            '/admin/',          # panel de Django
            '/static/',         # archivos estáticos
            '/media/',          # archivos de medios
            '/cuenta/',         # perfil, cambio de datos, etc.
            '/servicios/',      # paso 1: revisar planes y detalles del servicio
            '/suscribirse/',    # paso 2: solicitar plan (procesar_suscripcion)
            '/promociones/',    # flujo completo de promociones (suscribir,
            '/clientes/',                   # primera promoción, mis promociones, tarjetas /p/...)
            '/gestion/',
            '/registration/', # rutas de trabajo del equipo
        )
        rutas_exentas = (
            '/',                # home
            '/signup/',
            '/logout/',
            '/registro/',       # paso 2: registro de usuarios nuevos
            '/panel/',  # panel personal del cliente
        )
        if path in rutas_exentas:
            return True
        return path.startswith(prefijos_exentos)
