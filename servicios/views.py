from django.shortcuts import get_object_or_404, render
from .models import Servicio, Plan

# (Tu vista pagina_principal aquí arriba...)

def detalle_servicio(request, slug):
    # Busca el servicio activo por su slug, si no existe devuelve error 404
    servicio = get_object_or_404(Servicio, slug=slug, activo=True)
    # Obtiene los planes activos de este servicio ordenados por el campo 'orden'
    planes = servicio.planes.filter(activo=True).order_by('orden')
    
    context = {
        'servicio': servicio,
        'planes': planes
    }
    return render(request, 'servicios/detalle_servicio.html', context)