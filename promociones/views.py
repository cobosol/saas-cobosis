# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from .models import Promocion, SolicitudPromocion
from servicios.models import Plan, Suscripcion
from clientes.models import PerfilCliente

def promociones(request):
    pass

"""@login_required
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
"""
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
"""
@login_required
def mis_promociones(request):
    # 1. Promociones ya activas/públicas
    promociones_activas = Promocion.objects.filter(
        cliente=request.user, 
        estado='publicado'
    ).order_by('-creado')

    promociones_proceso = Promocion.objects.filter(
        cliente=request.user, 
        estado='pendiente'
    ).order_by('-creado')

    # 2. Solicitudes en proceso (pendientes de pago/diseño)
    solicitudes = SolicitudPromocion.objects.filter(
        usuario=request.user
    ).exclude(estado='activa').order_by('-fecha_solicitud')

    context = {
        'promociones_activas': promociones_activas,
        'promociones_proceso': promociones_proceso,
        'solicitudes': solicitudes,
    }
    return render(request, 'promociones/mis_promociones.html', context)
"""
@login_required(login_url='/login/')
def suscribir_promocion(request):
    """
    Suscribe al usuario a un plan de promociones y crea la primera promoción.
    Valida que no tenga suscripción activa previa.
    """
    planes = Plan.objects.filter(servicio__slug='promociones', activo=True).order_by('precio')
    
    if request.method == 'POST':
        plan_id = request.POST.get('plan_id')
        plan = get_object_or_404(Plan, id=plan_id, activo=True)
        
        #  VALIDACIÓN 1: Verificar si ya tiene suscripción activa o solicitada
        suscripcion_existente = Suscripcion.objects.filter(
            usuario=request.user,
            plan__servicio__slug='promociones',
            estado__in=['activa', 'solicitada']
        ).first()
        
        if suscripcion_existente:
            messages.warning(
                request, 
                f'Ya tienes una suscripción activa al plan "{suscripcion_existente.plan.nombre}". '
                'Puedes crear promociones adicionales desde tu panel.'
            )
            return redirect('crear_promocion_adicional')
        
        # VALIDACIÓN 2: Verificar límite de promociones del plan
        if not plan.permite_mas_promociones(request.user):
            messages.error(request, f'El plan "{plan.nombre}" no permite más promociones.')
            return redirect('panel_cliente')
        
        try:
            with transaction.atomic():
                # Crear la solicitud de promoción
                solicitud = _crear_solicitud_desde_post(request, plan)
                
                # Crear la suscripción solicitada
                Suscripcion.objects.create(
                    usuario=request.user,
                    plan=plan,
                    estado='solicitada',
                    fecha_fin=timezone.localdate() + timedelta(days=plan.vigencia_dias)
                )
                
                messages.success(
                    request, 
                    f'¡Solicitud enviada con éxito para el plan "{plan.nombre}"! '
                    'Nos pondremos en contacto contigo para el diseño y la activación.'
                )
        except Exception as e:
            print(f"ERROR COMPLETO: {e}")
            print(f"TIPO DE ERROR: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            messages.error(request, f'Error al procesar la solicitud: {str(e)}')
        
        return redirect('panel_cliente')
    
    context = {
        'planes': planes,
        'modo': 'suscripcion',  # Indica que es suscripción inicial
        'titulo_pagina': 'Suscríbete y Crea tu Primera Promoción',
    }
    return render(request, 'promociones/crear_promocion.html', context)