from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Promocion, SolicitudPromocion
from servicios.models import Plan
from clientes.models import Suscripcion, PerfilCliente

def promociones(request):
    pass

@login_required
def crear_promocion(request):
    # Obtenemos todos los planes activos del servicio Promociones
    planes = Plan.objects.filter(servicio__slug='promociones', activo=True).order_by('precio')
    
    if request.method == 'POST':
        plan_id = request.POST.get('plan_id')
        plan = get_object_or_404(Plan, id=plan_id, activo=True)
        
        datos = {}
        if plan.tipo_formulario == 'evento':
            datos['titulo'] = request.POST.get('titulo_evento')
            datos['fecha'] = request.POST.get('fecha_evento')
            datos['hora'] = request.POST.get('hora_evento')
            datos['lugar'] = request.POST.get('lugar_evento')
            datos['informacion'] = request.POST.get('info_evento')

            #solicitud = Promocion.objects.create(
            #            cliente=request.user,
            #            estado='pendiente',
            #            tipo = plan.tipo_formulario,
            #            titulo = datos['titulo'],
            #            descripcion = datos['informacion'],
            #            fecha_evento = datos['fecha'],
            #            lugar = datos['lugar']
            #        )
        elif plan.tipo_formulario == 'negocio':
            datos['nombre_negocio'] = request.POST.get('nombre_negocio')
            datos['rubro'] = request.POST.get('rubro_negocio')
            datos['telefono'] = request.POST.get('telefono_negocio')
            datos['descripcion'] = request.POST.get('descripcion_negocio')

            #solicitud = Promocion.objects.create(
            #                cliente=request.user,
            #                estado='pendiente',
            #                tipo = plan.tipo_formulario,
            #                titulo = datos['titulo'],
            #                descripcion = datos['informacion'],
            #            )
        else:
            datos['titulo'] = request.POST.get('titulo_generico')
            datos['descripcion'] = request.POST.get('descripcion_generica')

        # Convertir diccionario a texto para SQLite
        datos_texto = ", ".join([f"{k}: {v}" for k, v in datos.items()])

        # Leer nuevos campos de imagen
        generar_ia = request.POST.get('generar_imagen_ia') == 'on'
        imagen_subida = request.FILES.get('imagen_subida')

        # Crear la solicitud
        solicitud = SolicitudPromocion.objects.create(
            usuario=request.user,
            plan=plan,
            tipo=plan.tipo_formulario if plan.tipo_formulario != 'ninguno' else 'evento',
            datos_recopilados=datos_texto,
            generar_imagen_ia=generar_ia,
            imagen_subida=imagen_subida,
            estado='pendiente'
        )
        
        # Crear Suscripcion solicitada (igual que en Gestiona)
        Suscripcion.objects.get_or_create(
            usuario=request.user,
            plan=plan,
            estado='solicitada',
            defaults={'fecha_fin': timezone.now()}
        )
        
        messages.success(request, f'¡Solicitud enviada con éxito para el plan "{plan.nombre}"! Nos pondremos en contacto contigo para el diseño y la activación.')
        return redirect('panel_cliente')

    context = {'planes': planes}
    return render(request, 'promociones/crear_promocion.html', context)

# En views.py
def ver_promocion(request, slug):
    promocion = get_object_or_404(Promocion, slug=slug, activa=True)
    
    if not promocion.esta_vigente:
        return render(request, 'promociones/promocion_expirada.html')

    relacionadas = Promocion.objects.filter(
        categoria=promocion.categoria, 
        activa=True
    ).exclude(id=promocion.id).order_by('-es_destacada', '-fecha_inicio')[:10]

    context = {
        'promocion': promocion,
        'relacionadas': relacionadas
    }
    return render(request, 'promociones/ver_promocion.html', context)

@login_required
def mis_promociones(request):
    # 1. Promociones ya activas/públicas
    promociones_activas = Promocion.objects.filter(
        cliente=request.user, 
        estado='publicado'
    ).order_by('-creado')

    # 2. Solicitudes en proceso (pendientes de pago/diseño)
    solicitudes = SolicitudPromocion.objects.filter(
        usuario=request.user
    ).exclude(estado='activa').order_by('-fecha_solicitud')

    context = {
        'promociones_activas': promociones_activas,
        'solicitudes': solicitudes,
    }
    return render(request, 'promociones/mis_promociones.html', context)