from django.shortcuts import render
from servicios.models import Servicio, Plan
from promociones.models import Categoria, Promocion

# Create your views here.
def inicio(request):
    print("En inicio")
    servicios = Servicio.objects.filter(activo=True).prefetch_related(
        'planes'
    ).filter(planes__activo=True).distinct()
    
    context = {
        'servicios': servicios
    }
    print(context) 
    return render(request, "index.html", context)

def inicio_promociones(request):
    def agrupar(queryset, n=3):
        lista = list(queryset)
        return [lista[i:i+n] for i in range(0, len(lista), n)]
    
    # Eventos (sin cambios)
    eventos = Promocion.objects.filter(estado='publicado', tipo='evento').order_by('-prioridad', '-fecha_evento')
    negocios = Promocion.objects.filter(estado='publicado', tipo='negocio').order_by('-prioridad', '-creado')
    planes = Plan.objects.filter(activo=True, servicio__nombre='Promociones').order_by('precio', '-orden')

    # --- NUEVO: Carrusel principal (máximo 18 promociones = 3 slides de 6) ---
    promociones_destacadas = Promocion.objects.filter(estado='publicado').order_by('-prioridad', '-creado')[:18]
    promociones_carrusel = agrupar(promociones_destacadas, 6)  # grupos de 6

    context = {
        # Carrusel principal
        'promociones_carrusel': promociones_carrusel,   # lista de listas de Promocion

        # Eventos
        'eventos_agrupados': agrupar(eventos[:9], 3),   # 3 slides de 3
        'categorias_eventos': Categoria.objects.filter(tipo='evento'),
        'total_eventos': eventos.count(),

        # Negocios
        'negocios_agrupados': agrupar(negocios[:9], 3),
        'categorias_negocios': Categoria.objects.filter(tipo='negocio'),
        'total_negocios': negocios.count(),

        'planes': planes,
    }
    
    return render(request, 'promociones/inicio.html', context)