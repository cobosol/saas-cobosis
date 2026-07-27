from django.shortcuts import render
from servicios.models import Servicio, Plan
from promociones.models import Categoria, Promocion

# Create your views here.
def inicio(request):
    
    servicios = Servicio.objects.filter(activo=True).prefetch_related(
        'planes'
    ).filter(planes__activo=True).distinct()
    
    context = {
        'servicios': servicios
    }
    return render(request, "index.html", context)

def inicio_promociones(request):
    def agrupar(queryset, n=3):
        lista = list(queryset)
        return [lista[i:i+n] for i in range(0, len(lista), n)]
    
    # Eventos
    eventos = Promocion.objects.filter(
        estado='publicado', 
        tipo='evento'
    ).order_by('-prioridad', '-fecha_evento')
    
    # Negocios
    negocios = Promocion.objects.filter(
        estado='publicado', 
        tipo='negocio'
    ).order_by('-prioridad', '-creado')

    planes = Plan.objects.filter(
        activo = True,
        servicio__nombre = 'Promociones'
    ).order_by('precio', '-orden')
        
    context = {
        # Carrusel de eventos
        'eventos_agrupados': agrupar(eventos[:9]),  # Máximo 9 eventos (3 slides)
        'categorias_eventos': Categoria.objects.filter(tipo='evento'),
        'total_eventos': eventos.count(),
        
        # Carrusel de negocios
        'negocios_agrupados': agrupar(negocios[:9]),  # Máximo 9 negocios (3 slides)
        'categorias_negocios': Categoria.objects.filter(tipo='negocio'),
        'total_negocios': negocios.count(),

        'planes': planes,
    }
    
    return render(request, 'promociones/inicio.html', context)