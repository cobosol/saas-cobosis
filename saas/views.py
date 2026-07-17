from django.shortcuts import render
from servicios.models import Servicio, Plan

# Create your views here.
def inicio(request):
    
    servicios = Servicio.objects.filter(activo=True).prefetch_related(
        'planes'
    ).filter(planes__activo=True).distinct()
    
    context = {
        'servicios': servicios
    }
    return render(request, "index.html", context)
