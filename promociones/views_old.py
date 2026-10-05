# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from .models import Promocion, SolicitudPromocion, TemplateCard, RSVP
from servicios.models import Plan, Suscripcion, check_plan_capability
from clientes.models import PerfilCliente

from django.utils.text import slugify
from .forms import SolicitudPromocion, SolicitudIAForm, SolicitudImagenForm, SolicitudPlantillaForm
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.contrib.sessions.models import Session

"""@login_required
def dashboard(request):
    user = request.user
    subscription = Suscripcion.objects.filter(usuario=user, estado='activa').first()
    active_promotions = Promocion.objects.filter(suscripcion__usuario = user, estado='publicada').count()
    total_promotions = Promocion.objects.filter(suscripcion__usuario = user).count()
    plan = subscription.plan if subscription else None
    context = {
        'subscription': subscription,
        'plan': plan,
        'active_promotions': active_promotions,
        'total_promotions': total_promotions,
        'promotions': Promocion.objects.filter(suscripcion__usuario = user).order_by('-creado'),
    }
    return render(request, 'promociones/dashboard.html', context)
"""

def _suscripcion_activa(user):
    return Suscripcion.objects.filter(
        usuario=user, plan__servicio__slug='promociones', estado='activa'
    ).first()

@login_required
def crear_promocion(request):
    """Pantalla de elección: plantilla / imagen propia / IA."""
    sub = _suscripcion_activa(request.user)
    if not sub:
        messages.warning(request, 'Necesitas una suscripción activa.')
        return redirect('suscribir_promocion')

    if not sub.plan.permite_mas_promociones(request.user):
        messages.error(request, f'Límite de {sub.plan.max_promociones} promociones alcanzado.')
        return redirect('promociones:mis_promociones')

    templates = TemplateCard.objects.filter(
        category__in=sub.plan.get_tipos_permitidos_list()
    )

    return render(request, 'promociones/crear/selector.html', {
        'suscripcion': sub,
        'plan': sub.plan,
        'templates': templates,
    })

@login_required
def crear_desde_plantilla(request, template_id):
    sub = _suscripcion_activa(request.user)
    template = get_object_or_404(TemplateCard, id=template_id)

    if request.method == 'POST':
        form = SolicitudPlantillaForm(request.POST, request.FILES, template=template)
        if form.is_valid():
            with transaction.atomic():
                sol = form.save(commit=False)
                sol.usuario = request.user
                sol.plan = sub.plan
                sol.modo = 'plantilla'
                sol.template_origen = template
                sol.tipo = template.category
                sol.estado = 'disenando'   # ya tiene plantilla → pasa directo a diseño
                sol.datos_recopilados = str(form.cleaned_data)
                sol.save()

            messages.success(request, '¡Solicitud creada! Nuestro equipo la está preparando.')
            return redirect('promociones:detalle_solicitud', pk=sol.pk)
    else:
        form = SolicitudPlantillaForm(template=template)

    return render(request, 'promociones/crear/desde_plantilla.html', {
        'form': form, 'template': template,
    })

@login_required
def crear_con_imagen(request):
    sub = _suscripcion_activa(request.user)

    if request.method == 'POST':
        form = SolicitudImagenForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                sol = form.save(commit=False)
                sol.usuario = request.user
                sol.plan = sub.plan
                sol.modo = 'imagen'
                sol.generar_imagen_ia = False
                sol.estado = 'aprobada'  # listo para publicar
                sol.save()

                # Crear la Promocion directamente (publicación instantánea)
                promo = Promocion.objects.create(
                    suscripcion=sub,
                    titulo=form.cleaned_data['titulo'],
                    descripcion=form.cleaned_data.get('descripcion', ''),
                    imagen=sol.imagen_subida,
                    tipo=form.cleaned_data.get('tipo', 'evento'),
                    fecha_evento=form.cleaned_data.get('fecha_evento') or timezone.now(),
                    lugar=form.cleaned_data.get('lugar', ''),
                    enlace_accion=form.cleaned_data.get('enlace_accion', ''),
                    estado='publicado',
                )
                sol.promocion_creada = promo
                sol.estado = 'activa'
                sol.save()

            messages.success(request, '¡Promoción publicada! Ya está visible.')
            return redirect('promociones:mis_promociones')
    else:
        form = SolicitudImagenForm()

    return render(request, 'promociones/crear/con_imagen.html', {'form': form})

@login_required
def crear_con_ia(request):
    sub = _suscripcion_activa(request.user)

    if request.method == 'POST':
        form = SolicitudIAForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                sol = form.save(commit=False)
                sol.usuario = request.user
                sol.plan = sub.plan
                sol.modo = 'ia'
                sol.generar_imagen_ia = True
                sol.estado = 'pendiente'   # entra a la cola de Cobosis
                sol.datos_recopilados = str(form.cleaned_data)
                sol.save()

            messages.success(
                request,
                '¡Solicitud enviada! Cobosis diseñará tu promoción y te la enviará para aprobación.'
            )
            return redirect('promociones:detalle_solicitud', pk=sol.pk)
    else:
        form = SolicitudIAForm()

    return render(request, 'promociones/crear/con_ia.html', {'form': form})

@login_required
def detalle_solicitud_cliente(request, pk):
    sol = get_object_or_404(SolicitudPromocion, pk=pk, usuario=request.user)
    return render(request, 'promociones/cliente/detalle_solicitud.html', {'sol': sol})

@login_required
def cliente_aprobar_diseno(request, pk):
    sol = get_object_or_404(SolicitudPromocion, pk=pk, usuario=request.user)
    if request.method == 'POST' and sol.estado == 'revision':
        with transaction.atomic():
            sol.estado = 'activa'
            sol.comentario_cliente = request.POST.get('comentario', '')
            sol.save()

            # Crear la Promocion final
            promo = Promocion.objects.create(
                suscripcion=sol.suscripcion if hasattr(sol, 'suscripcion') else None,
                titulo=sol.datos_recopilados[:200],
                descripcion=sol.datos_recopilados,
                imagen=sol.imagen_generada or sol.imagen_subida,
                tipo=sol.tipo,
                estado='publicado',
                fecha_evento=timezone.now(),
            )
            sol.promocion_creada = promo
            sol.save()

        messages.success(request, '¡Diseño aprobado y publicado!')
    return redirect('promociones:detalle_solicitud', pk=pk)

@login_required
def cliente_solicitar_cambios(request, pk):
    sol = get_object_or_404(SolicitudPromocion, pk=pk, usuario=request.user)
    if request.method == 'POST':
        sol.estado = 'disenando'
        sol.comentario_cliente = request.POST.get('comentario', '')
        sol.save()
        messages.info(request, 'Le enviamos tus comentarios al equipo de Cobosis.')
    return redirect('promociones:detalle_solicitud', pk=pk)

@staff_member_required
def panel_promociones(request):
    estado = request.GET.get('estado', 'pendiente')
    modo   = request.GET.get('modo', 'plantilla')
    print(estado)

    qs = SolicitudPromocion.objects.select_related(
        'usuario', 'plan', 'promocion_creada__template'
    )
    if estado in dict(SolicitudPromocion.ESTADO):
        qs = qs.filter(estado=estado)
    if modo in dict(SolicitudPromocion.MODO):
        qs = qs.filter(modo=modo)

    conteos = {
        'pendiente': SolicitudPromocion.objects.filter(estado='pendiente').count(),
        'disenando': SolicitudPromocion.objects.filter(estado='disenando').count(),
        'revision':  SolicitudPromocion.objects.filter(estado='revision').count(),
        'activa':    SolicitudPromocion.objects.filter(estado='activa').count(),
        'rechazada': SolicitudPromocion.objects.filter(estado='rechazada').count(),
    }

    return render(request, 'promociones/panel/lista.html', {
        'solicitudes': qs,
        'estado_actual': estado,
        'modo_actual': modo,
        'estados': SolicitudPromocion.ESTADO,
        'modos': SolicitudPromocion.MODO,
        'conteos': conteos,
    })

@staff_member_required
def admin_detalle_solicitud(request, pk):
    sol = get_object_or_404(SolicitudPromocion, pk=pk)
    return render(request, 'promociones/panel/detalle.html', {'sol': sol})

@staff_member_required
def admin_cambiar_estado(request, pk, nuevo_estado):
    sol = get_object_or_404(SolicitudPromocion, pk=pk)
    if request.method == 'POST' and nuevo_estado in dict(SolicitudPromocion.ESTADO):
        sol.estado = nuevo_estado
        sol.comentario_admin = request.POST.get('comentario', '')
        sol.save()
        messages.success(request, f'Estado cambiado a "{sol.get_estado_display()}".')
    return redirect('promociones:admin_detalle_solicitud', pk=pk)

@staff_member_required
def admin_subir_diseno(request, pk):
    """Cobosis sube el diseño terminado y lo manda al cliente para revisión."""
    sol = get_object_or_404(SolicitudPromocion, pk=pk)
    if request.method == 'POST':
        sol.imagen_generada = request.FILES.get('imagen_generada') or sol.imagen_generada
        sol.comentario_admin = request.POST.get('comentario_admin', sol.comentario_admin)
        sol.estado = 'revision'   # → el cliente debe aprobar
        sol.save()
        messages.success(request, 'Diseño enviado al cliente para su revisión.')
    return redirect('promociones:admin_detalle_solicitud', pk=pk)

@login_required
def create_promotion_step1(request):
    # Obtener plan activo
    subscription = Suscripcion.objects.filter(user=request.user, status='active').first()
    if not subscription:
        messages.error(request, 'No tienes una suscripción activa.')
        return redirect('plans:choose')
    plan = subscription.plan

    # Obtener categorías permitidas según capacidades del plan
    allowed_categories = plan.capabilities.get('allowed_categories', [])
    templates = TemplateCard.objects.filter(category__in=allowed_categories)

    if request.method == 'POST':
        # Guardar la plantilla seleccionada en sesión
        template_id = request.POST.get('template')
        request.session['promo_template_id'] = template_id
        return redirect('promotions:create_step2')

    return render(request, 'promotions/create_step1.html', {'templates': templates})

@login_required
def create_promotion_step2(request):
    template_id = request.session.get('promo_template_id')
    if not template_id:
        return redirect('promotions:create_step1')
    template = get_object_or_404(TemplateCard, id=template_id)

    # Validar límite de promociones activas
    subscription = Suscripcion.objects.filter(user=request.user, status='active').first()
    if not subscription:
        messages.error(request, 'Suscripción no activa.')
        return redirect('plans:choose')
    plan = subscription.plan
    active_count = Promocion.objects.filter(user=request.user, status='published').count()
    if active_count >= plan.max_active_promotions:
        messages.error(request, f'Has alcanzado el límite de {plan.max_active_promotions} promociones activas.')
        return redirect('promotions:dashboard')

    # Formulario dinámico basado en fields_schema
    if request.method == 'POST':
        form = PromotionStepForm(template, request.POST, request.FILES)
        if form.is_valid():
            promotion = form.save(commit=False)
            promotion.user = request.user
            promotion.template = template
            promotion.slug = slugify(promotion.title) + '-' + str(timezone.now().timestamp())
            promotion.save()
            # Limpiar sesión
            del request.session['promo_template_id']
            messages.success(request, '¡Promoción creada exitosamente!')
            return redirect('promotions:dashboard')
    else:
        form = PromotionStepForm(template)

    return render(request, 'promotions/create_step2.html', {'form': form, 'template': template})

def promociones(request):
    pass

def promotion_public(request, slug):
    promotion = get_object_or_404(Promocion, slug=slug)
    
    # 1. Verificar estado de la promoción
    if promotion.status != 'published':
        return render(request, 'public/not_available.html', {'reason': 'Esta promoción no está publicada.'})
    
    # 2. Verificar suscripción activa del dueño
    subscription = Suscripcion.objects.filter(user=promotion.user, status='active').first()
    if not subscription or subscription.end_date < timezone.now():
        if subscription and subscription.end_date < timezone.now():
            subscription.status = 'expired'
            subscription.save()
        return render(request, 'public/not_available.html', {'reason': 'La suscripción ha expirado.'})
    
    # 3. Incrementar visitas
    promotion.visits += 1
    promotion.save(update_fields=['visits'])

    # 4. Verificar si el plan permite RSVP
    can_rsvp = subscription.plan.capabilities.get('can_rsvp', False)
    rsvp_success = False
    rsvp_error = None

    # 5. Procesar el POST del RSVP
    if request.method == 'POST' and can_rsvp:
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        
        # Validaciones básicas
        if not name or not email:
            rsvp_error = 'Nombre y email son obligatorios.'
        elif '@' not in email:
            rsvp_error = 'Ingresa un email válido.'
        else:
            # Evitar duplicados (mismo email para la misma promoción)
            existing = RSVP.objects.filter(promotion=promotion, email=email).first()
            if existing:
                rsvp_error = 'Ya confirmaste asistencia con este correo.'
            else:
                # Guardar el RSVP
                RSVP.objects.create(
                    promotion=promotion,
                    name=name,
                    email=email
                )
                # Incrementar contador de clics/confirmaciones
                promotion.rsvp_clicks += 1
                promotion.save(update_fields=['rsvp_clicks'])
                rsvp_success = True
                # Opcional: guardar en sesión para no mostrar el formulario de nuevo
                request.session[f'rsvp_{promotion.id}'] = True

    # Verificar si este usuario ya confirmó (para ocultar formulario)
    already_rsvped = request.session.get(f'rsvp_{promotion.id}', False)
    
    relacionadas = Promocion.objects.filter(
        categoria=promotion.categoria, 
        estado='publicado'
    ).exclude(id=promotion.id).order_by('-destacado', '-fecha_evento')[:10]

    context = {
        'promocion': promotion,
        'can_rsvp': can_rsvp,
        'rsvp_success': rsvp_success,
        'rsvp_error': rsvp_error,
        'already_rsvped': already_rsvped,
        'rsvp_count': promotion.rsvps.count(),  # Total de confirmados
        'relacionadas': relacionadas,
    }
    return render(request, 'promociones/ver_promocion.html', context)

def ver_promocion(request, slug):
    promocion = get_object_or_404(Promocion, slug=slug) #, estado='publicado'
    
    """ if not promocion.esta_vigente:
        return render(request, 'promociones/promocion_expirada.html') """
    
    suscripcion = Suscripcion.objects.filter(user=promocion.user, status='active').first()
    promocion.visits += 1
    promocion.save(update_fields=['visits'])
    # Manejar RSVP si el plan lo permite
    can_rsvp = suscripcion.plan.capabilities.get('can_rsvp', False)
    if request.method == 'POST' and can_rsvp:
        # procesar RSVP
        pass

    relacionadas = Promocion.objects.filter(
        categoria=promocion.categoria, 
        estado='publicado'
    ).exclude(id=promocion.id).order_by('-destacado', '-fecha_evento')[:10]

    context = {
        'promocion': promocion,
        'relacionadas': relacionadas
    }
    print(context)
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

    print(suscripcion_activa)

    # Obtener promociones activas y solicitudes
    promociones_activas = SolicitudPromocion.objects.filter(
        usuario=request.user,
        estado__in=['disenando', 'activa']
    ).order_by('-fecha_solicitud')

    print(f'promociones_activas {promociones_activas}')

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

@login_required
def edit_promotion(request, pk):
    promotion = get_object_or_404(Promocion, pk=pk, user=request.user)
    
    # Evitar editar promociones activas a menos que se pausen primero (seguridad)
    if promotion.estado == 'published':
        messages.warning(request, 'Para editar, primero debes pausar la promoción.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = PromotionForm(request.POST, request.FILES, instance=promotion)
        if form.is_valid():
            form.save()
            messages.success(request, '¡Promoción actualizada correctamente!')
            return redirect('promotions:dashboard')
    else:
        form = PromotionForm(instance=promotion)

    context = {
        'form': form,
        'promotion': promotion,
        'is_editing': True,
    }
    return render(request, 'promociones/edit.html', context)