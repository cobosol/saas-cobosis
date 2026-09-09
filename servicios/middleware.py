from django.shortcuts import redirect
from django.urls import reverse
from .models import Suscripcion
from django.utils import timezone

class ActiveSubscriptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Excluir URLs de administración, login, etc.
            exempt_urls = [reverse('login'), reverse('logout'), reverse('registro'),
                           reverse('inicio'),]
            if request.path not in exempt_urls and not request.path.startswith('/admin/'):
                subscription = Suscripcion.objects.filter(usuario=request.user, estado='active').first()
                if not subscription or subscription.fecha_fin < timezone.now():
                    # Si expiró, cambiar estado y redirigir
                    if subscription:
                        subscription.estado = 'vencida'
                        subscription.save()
                    # Redirigir a selección de plan
                    return redirect('inicio')
        return self.get_response(request)