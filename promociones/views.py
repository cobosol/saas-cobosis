# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
<<<<<<< Updated upstream
from .models import Promocion
from servicios.models import Plan
from clientes.models import Suscripcion, PerfilCliente
=======
from django.db import transaction
from datetime import timedelta
from .models import Promocion, SolicitudPromocion
from servicios.models import Plan, Suscripcion
from clientes.models import PerfilCliente
>>>>>>> Stashed changes

def promociones(request):
    pass

"""@login_required
def crear_promocion(request):
    # Obtenemos todos los planes activos del servicio Promociones
    planes = Plan.objects.filter(servicio__slug='promociones', activo=True).order_by('precio')
    
    if request.method == 'POST':
        plan_id = request.POST.get('plan_id')
        plan = get_object_or_404(Plan, id=plan_id, activo=True)
        
        # Recopilar datos dinámicamente según el tipo de formulario del plan
        datos = {}
        if plan.tipo_formulario == 'evento':
            datos['titulo'] = request.POST.get('titulo_evento')
            datos['fecha'] = request.POST.get('fecha_evento')
            datos['hora'] = request.POST.get('hora_evento')
            datos['lugar'] = request.POST.get('lugar_evento')
            datos['informacion'] = request.POST.get('info_evento')
        elif plan.tipo_formulario == 'negocio':
            datos['nombre_negocio'] = request.POST.get('nombre_negocio')
            datos['rubro'] = request.POST.get('rubro_negocio')
            datos['telefono'] = request.POST.get('telefono_negocio')
            datos['descripcion'] = request.POST.get('descripcion_negocio')
        else:
            datos['titulo'] = request.POST.get('titulo_generico')
            datos['descripcion'] = request.POST.get('descripcion_generica')

        # 1. Crear la Solicitud de Promoción con los datos
        solicitud = Promocion.objects.create(
            cliente=request.user,
            estado='pendiente'
        )
        
        # 2. Crear la Suscripción en estado "solicitada" para tu gestión
        Suscripcion.objects.get_or_create(
            usuario=request.user,
            plan=plan,
            estado='solicitada',
            defaults={'fecha_vencimiento': timezone.now()} # Temporal, se actualiza al aprobar
        )
        
        messages.success(request, f'¡Solicitud enviada con éxito para el plan "{plan.nombre}"! Nos pondremos en contacto contigo para el diseño y la activación.')
        return redirect('panel_cliente')

    context = {
        'planes': planes
    }
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
<<<<<<< Updated upstream

=======
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
        
        # ✅ VALIDACIÓN 1: Verificar si ya tiene suscripción activa o solicitada
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
        
        # ✅ VALIDACIÓN 2: Verificar límite de promociones del plan
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

@login_required(login_url='/login/')
def mis_promociones(request):
    # Obtener suscripción activa
    suscripcion_activa = Suscripcion.objects.filter(
        usuario=request.user,
        plan__servicio__slug='promociones',
        estado='activa'
    ).first()
    
    # Obtener promociones activas y solicitudes
    promociones_activas = SolicitudPromocion.objects.filter(
        usuario=request.user,
        estado__in=['aprobada', 'publicada']
    ).order_by('-fecha_solicitud')
    
    solicitudes = SolicitudPromocion.objects.filter(
        usuario=request.user,
        estado__in=['pendiente', 'disenando']
    ).order_by('-fecha_solicitud')
    
    # Calcular promociones restantes
    promociones_restantes = None
    if suscripcion_activa and suscripcion_activa.plan.max_promociones > 0:
        total_creadas = SolicitudPromocion.objects.filter(
            usuario=request.user,
            plan=suscripcion_activa.plan
        ).count()
        promociones_restantes = suscripcion_activa.plan.max_promociones - total_creadas
    
    context = {
        'promociones_activas': promociones_activas,
        'solicitudes': solicitudes,
        'suscripcion_activa': suscripcion_activa,
        'promociones_restantes': promociones_restantes,
    }
    return render(request, 'promociones/mis_promociones.html', context)

# ============================================================
# VISTA 2: CREAR PROMOCIÓN ADICIONAL
# Se usa cuando el usuario YA tiene una suscripción activa
# ============================================================
@login_required(login_url='/login/')
def crear_promocion_adicional(request):
    """
    Crea promociones adicionales para usuarios que ya tienen suscripción activa.
    """
    # Obtener la suscripción activa del usuario
    suscripcion_activa = Suscripcion.objects.filter(
        usuario=request.user,
        plan__servicio__slug='promociones',
        estado='activa'
    ).first()
    
    if not suscripcion_activa:
        messages.warning(request, 'No tienes una suscripción activa. Debes suscribirte primero.')
        return redirect('suscribir_promocion')
    
    plan = suscripcion_activa.plan
    
    # ✅ Validar límite de promociones
    if not plan.permite_mas_promociones(request.user):
        messages.error(
            request, 
            f'Has alcanzado el límite de {plan.max_promociones} promociones '
            f'para el plan "{plan.nombre}".'
        )
        return redirect('mis_promociones')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                solicitud = _crear_solicitud_desde_post(request, plan)
                messages.success(request, '¡Promoción adicional solicitada con éxito!')
        except Exception as e:
            messages.error(request, f'Error al procesar: {str(e)}')
        
        return redirect('mis_promociones')
    
    context = {
        'plan_actual': plan,
        'suscripcion': suscripcion_activa,
        'modo': 'adicional',  # Indica que es promoción adicional
        'titulo_pagina': f'Crear Promoción Adicional - Plan {plan.nombre}',
        'tipos_permitidos': plan.get_tipos_permitidos_list(),
    }
    return render(request, 'promociones/crear_promocion.html', context)

# ============================================================
# FUNCIÓN AUXILIAR: Crear solicitud desde POST
# ============================================================
def _crear_solicitud_desde_post(request, plan):
    """
    Crea una SolicitudPromocion a partir de los datos del POST.
    """
    tipo = request.POST.get('tipo_formulario') or plan.tipo_formulario or 'evento'
    
    solicitud = SolicitudPromocion.objects.create(
        usuario=request.user,
        plan=plan,
        tipo=tipo,
        estado='pendiente',
        generar_imagen_ia=request.POST.get('generar_imagen_ia') == 'on',
        imagen_subida=request.FILES.get('imagen_subida'),
    )
    
    # Guardar campos según el tipo
    if tipo == 'evento':
        solicitud.titulo_evento = request.POST.get('titulo_evento', '')
        solicitud.fecha_evento = request.POST.get('fecha_evento') or None
        solicitud.hora_evento = request.POST.get('hora_evento') or None
        solicitud.lugar_evento = request.POST.get('lugar_evento', '')
        solicitud.info_evento = request.POST.get('info_evento', '')
        solicitud.datos_recopilados = f"Título: {solicitud.titulo_evento}, Lugar: {solicitud.lugar_evento}"
        
    elif tipo == 'negocio':
        solicitud.nombre_negocio = request.POST.get('nombre_negocio', '')
        solicitud.rubro_negocio = request.POST.get('rubro_negocio', '')
        solicitud.telefono_negocio = request.POST.get('telefono_negocio', '')
        solicitud.descripcion_negocio = request.POST.get('descripcion_negocio', '')
        solicitud.datos_recopilados = f"Negocio: {solicitud.nombre_negocio}, Rubro: {solicitud.rubro_negocio}"
        
    else:
        solicitud.titulo_generico = request.POST.get('titulo_generico', '')
        solicitud.descripcion_generica = request.POST.get('descripcion_generica', '')
        solicitud.datos_recopilados = f"Título: {solicitud.titulo_generico}"
    
    solicitud.save()
    return solicitud
>>>>>>> Stashed changes
