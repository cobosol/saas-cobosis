"""
Vistas del módulo de promociones.

FLUJO DE NEGOCIO (flujo principal del cliente):
    Paso 1: El usuario revisa los planes en el detalle del servicio (app 'servicios')
            y pulsa "Solicitar plan" -> procesar_suscripcion(plan_id).
    Paso 2: Si no está autenticado -> redirige al REGISTRO conservando el destino
            (?next=...). Tras registrarse, el flujo continúa donde lo dejó.
            Si ya está registrado -> suscribir_promocion: formulario con los datos
            del negocio y demás detalles.
    Paso 3: primera_promocion: formulario de la primera promoción (el tipo lo
            define el plan), con imagen propia o diseño con IA.
    Paso 4: Todo queda en la parte administrativa: Suscripcion('solicitada') +
            SolicitudPromocion('pendiente'). El equipo contacta al cliente para
            el pago, activa la cuenta, diseña la tarjeta y la publica.

VISTAS DE CLIENTE:
    mis_promociones        -> panel del cliente (tarjetas publicadas + solicitudes)
    suscribir_promocion    -> paso 2.1 (datos del negocio)
    primera_promocion      -> paso 3 (primera promoción)
    crear_promocion        -> promociones adicionales (requiere plan activo)
    solicitud_enviada      -> confirmación del paso 4
    ver_promocion          -> tarjeta pública (/p/<slug>/)
    listado_publicadas     -> landing: todas las promociones publicadas

VISTAS DEL EQUIPO ADMINISTRATIVO (staff):
    admin_solicitudes        -> bandeja de solicitudes con filtros
    admin_solicitud_detalle  -> detalle completo + acciones
    admin_cambiar_estado     -> cambiar estado / notas internas
    admin_publicar_promocion -> crear la tarjeta, publicarla y activar la suscripción
"""
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.db.models import F, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from urllib.parse import quote

from clientes.models import User  # noqa: F401  (import explícito por claridad)
from servicios.models import Plan, Suscripcion

from .forms import (AdminCambiarEstadoForm, AdminPromocionForm, DatosNegocioForm,
                    PromocionSolicitudForm)
from .models import DatosNegocio, Promocion, SolicitudPromocion

logger = logging.getLogger(__name__)

# URL de registro usada cuando el flujo requiere autenticación de un usuario nuevo
URL_REGISTRO = 'registro'

ESTADOS_CON_PROMO = ['pendiente', 'disenando', 'aprobada', 'publicada']


# ==============================================================================
# Helpers internos
# ==============================================================================
def _url_registro(next_url=None):
    """URL de registro preservando el destino para continuar el flujo."""
    if not next_url:
        return reverse(URL_REGISTRO)
    return f'{reverse(URL_REGISTRO)}?next={quote(next_url)}'

def _suscripcion_promociones(usuario):
    """Suscripción ACTIVA del usuario en el servicio de promociones (o None)."""
    return (Suscripcion.objects
            .select_related('plan', 'plan__servicio')
            .filter(usuario=usuario,
                    plan__servicio__slug='promociones',
                    estado='activa')
            .order_by('-fecha_inicio')
            .first())

def _promociones_restantes(usuario, plan):
    """Cuántas promociones le quedan al usuario según su plan (None = ilimitadas)."""
    if plan.max_promociones == 0:
        return None
    usadas = SolicitudPromocion.objects.filter(
        usuario=usuario, plan=plan, estado__in=ESTADOS_CON_PROMO).count()
    return max(plan.max_promociones - usadas, 0)

def _puede_crear_promocion(usuario, plan):
    """¿Puede el usuario crear otra promoción con este plan?

    Réplica de la lógica de Plan.permite_mas_promociones (servicios.models) para
    no acoplarse al nombre exacto del método del modelo.
    """
    if plan.max_promociones == 0:  # ilimitadas
        return True
    hay_sub = Suscripcion.objects.filter(
        usuario=usuario, plan=plan, estado__in=['activa', 'solicitada']).exists()
    if not hay_sub:  # primera suscripción
        return True
    usadas = SolicitudPromocion.objects.filter(
        usuario=usuario, plan=plan, estado__in=ESTADOS_CON_PROMO).count()
    return usadas < plan.max_promociones

def _obtener_plan_promociones(plan_id):
    """Plan activo del servicio de promociones (o 404)."""
    return get_object_or_404(Plan, id=plan_id, activo=True,
                             servicio__slug='promociones')

# ==============================================================================
# Panel del cliente — Bandeja de mis promociones
# ==============================================================================
ORDEN_FLUJO = ['pendiente', 'disenando', 'aprobada', 'publicada']

def contexto_bandeja(usuario):
    """Contexto completo de la BANDEJA DE PROMOCIONES de un cliente.

    Se usa en la vista `mis_promociones` y puede reutilizarse para incrustar
    la bandeja DENTRO del panel propio del cliente (ver README, sección 4):

        from promociones.views import contexto_bandeja
        context.update(contexto_bandeja(request.user))
        # y en la plantilla del panel:
        # {% include 'promociones/partials/bandeja_promociones.html' %}

    Devuelve:
        plan_actual / sub_estado / sub_fecha_fin -> estado del plan (activa o solicitada)
        puede_crear / promociones_restantes      -> CTA y límite del plan
        en_proceso  -> [{solicitud, paso (1..4), tarjeta_borrador}]  solicitudes vivas
        publicadas  -> [{solicitud, tarjeta}]                        tarjetas visibles
        rechazadas  -> [{solicitud, motivo}]                         historial
        total_proceso / total_publicadas / vistas_totales -> cifras resumen
    """
    solicitudes = (SolicitudPromocion.objects
                   .filter(usuario=usuario)
                   .select_related('plan', 'plan__servicio', 'promocion_creada')
                   .order_by('-fecha_solicitud'))

    # Suscripción más reciente del servicio (activa o solicitada) para el estado del plan
    sub = (Suscripcion.objects
           .filter(usuario=usuario, plan__servicio__slug='promociones')
           .exclude(estado__in=['cancelada', 'vencida'])
           .select_related('plan', 'plan__servicio')
           .order_by('-id')
           .first())
    plan = sub.plan if sub else None

    en_proceso, publicadas, rechazadas = [], [], []
    for sol in solicitudes:
        tarjeta = sol.promocion_creada
        if sol.estado == 'rechazada':
            rechazadas.append({'solicitud': sol, 'motivo': sol.notas_admin})
        elif tarjeta and tarjeta.publicada:
            publicadas.append({'solicitud': sol, 'tarjeta': tarjeta})
        else:
            en_proceso.append({
                'solicitud': sol,
                'paso': (ORDEN_FLUJO.index(sol.estado) + 1
                         if sol.estado in ORDEN_FLUJO else 1),
                # Tarjeta diseñada pero aún NO publicada (borrador): el cliente
                # puede previsualizarla mientras el equipo la aprueba/publica.
                'tarjeta_borrador': tarjeta if (tarjeta and not tarjeta.publicada) else None,
            })

    puede_crear = bool(sub and sub.estado == 'activa' and plan
                       and _puede_crear_promocion(usuario, plan))
    restantes = _promociones_restantes(usuario, plan) if plan else 0

    return {
        'plan_actual': plan,
        'sub_estado': sub.estado if sub else None,
        'sub_fecha_fin': sub.fecha_fin if sub else None,
        'puede_crear': puede_crear,
        'promociones_restantes': restantes,
        'en_proceso': en_proceso,
        'publicadas': publicadas,
        'rechazadas': rechazadas,
        'total_proceso': len(en_proceso),
        'total_publicadas': len(publicadas),
        'vistas_totales': sum(i['tarjeta'].vistas for i in publicadas),
    }


@login_required(login_url=URL_REGISTRO)
def mis_promociones(request):
    """BANDEJA DEL CLIENTE: estado del plan, solicitudes en curso (con el paso
    del flujo de cada una), tarjetas publicadas y historial de rechazadas.

    Plantilla standalone:  promociones/mis_promociones.html
    Versión incrustable en el panel del cliente:
        {% include 'promociones/partials/bandeja_promociones.html' %}
    """
    context = contexto_bandeja(request.user)
    context['titulo_pagina'] = 'Mis Promociones'
    return render(request, 'promociones/mis_promociones.html', context)

# ==============================================================================
# Paso 2 / 2.1 — Suscripción: datos del negocio
# ==============================================================================
@login_required(login_url=URL_REGISTRO)
def suscribir_promocion(request, plan_id):
    """Paso 2.1 del flujo: formulario de suscripción con datos del negocio.

    Llega aquí desde procesar_suscripcion (app 'servicios') cuando el plan es de
    pago, o tras completar el registro (via ?next=).
    """
    plan = _obtener_plan_promociones(plan_id)

    # Si ya tiene este plan solicitado/activo Y ya nos dio sus datos de negocio,
    # no repetir la suscripción: va directo a crear la promoción.
    ya_tiene = Suscripcion.objects.filter(
        usuario=request.user, plan=plan, estado__in=['activa', 'solicitada']).exists()
    tiene_datos = DatosNegocio.objects.filter(usuario=request.user).exists()
    if ya_tiene and tiene_datos:
        messages.info(request,
                      'Ya tienes este plan solicitado. Puedes enviar tu promoción directamente.')
        return redirect('promociones:crear_promocion')

    instancia = DatosNegocio.objects.filter(usuario=request.user).first()

    if request.method == 'POST':
        form = DatosNegocioForm(request.POST, instance=instancia)
        if form.is_valid():
            datos_negocio = form.save(commit=False)
            datos_negocio.usuario = request.user
            datos_negocio.save()
            messages.success(request,
                             'Datos del negocio guardados. Ahora cuéntanos sobre tu promoción.')
            return redirect('promociones:primera_promocion', plan_id=plan.id)
    else:
        form = DatosNegocioForm(instance=instancia)

    return render(request, 'promociones/suscribir_promocion.html', {
        'plan': plan,
        'form': form,
        'titulo_pagina': 'Suscribirse a Promociones',
    })

# ==============================================================================
# Paso 3 — Primera promoción
# ==============================================================================
@login_required(login_url=URL_REGISTRO)
def primera_promocion(request, plan_id):
    """Paso 3 del flujo: formulario de la primera promoción.

    Al enviarlo se crean en una sola transacción:
        - la Suscripcion en estado 'solicitada' (si no existía),
        - la SolicitudPromocion en estado 'pendiente' con el snapshot de los
          datos del negocio + los campos de la promoción.
    Eso es exactamente lo que el equipo administrativo necesita para contactar
    al cliente (pago y activación).
    """
    plan = _obtener_plan_promociones(plan_id)

    # El paso anterior (datos del negocio) es obligatorio
    datos_negocio = DatosNegocio.objects.filter(usuario=request.user).first()
    if not datos_negocio:
        return redirect('promociones:suscribir_promocion', plan_id=plan.id)

    # Evitar solicitudes duplicadas para el mismo plan
    if SolicitudPromocion.objects.filter(
            usuario=request.user, plan=plan,
            estado__in=['pendiente', 'disenando']).exists():
        messages.info(request,
                      'Ya tienes una solicitud en curso para este plan. '
                      'El equipo se pondrá en contacto contigo.')
        return redirect('promociones:mis_promociones')

    tipo = plan.tipo_formulario if plan.tipo_formulario in ('evento', 'negocio', 'ninguno') else 'ninguno'

    if request.method == 'POST':
        form = PromocionSolicitudForm(request.POST, request.FILES, tipo=tipo,
                                      datos_negocio=datos_negocio, plan=plan)
        if form.is_valid():
            with transaction.atomic():
                # 1) Suscripción solicitada (o existente si el plan ya estaba)
                sub = Suscripcion.objects.filter(
                    usuario=request.user, plan=plan,
                    estado__in=['activa', 'solicitada']).first()
                if not sub:
                    sub = Suscripcion.objects.create(
                        usuario=request.user, plan=plan, estado='solicitada')

                # 2) Solicitud de promoción con toda la información
                solicitud = form.save(commit=False)
                solicitud.usuario = request.user
                solicitud.plan = plan
                solicitud.suscripcion = sub
                solicitud.estado = 'pendiente'
                solicitud.save()

            logger.info('Nueva solicitud de promoción #%s (%s, plan %s) de %s',
                        solicitud.pk, solicitud.tipo, plan.nombre, request.user.username)
            messages.success(
                request,
                '¡Solicitud enviada! Nuestro equipo te contactará para los temas de '
                'pago y activación de tu cuenta.')
            return redirect('promociones:solicitud_enviada', solicitud_id=solicitud.id)
    else:
        form = PromocionSolicitudForm(tipo=tipo, datos_negocio=datos_negocio, plan=plan)

    return render(request, 'promociones/primera_promocion.html', {
        'plan': plan,
        'tipo': tipo,
        'form': form,
        'titulo_pagina': 'Tu primera promoción',
    })

# ==============================================================================
# Promociones adicionales (con plan activo)
# ==============================================================================
@login_required(login_url=URL_REGISTRO)
def crear_promocion(request):
    """Formulario para promociones adicionales con el plan ya activo.

    Respeta el límite de promociones del plan (Plan.permitir_mas_promociones)
    y los tipos de promoción permitidos (Plan.get_tipos_permitidos_list).
    """
    sub_activa = _suscripcion_promociones(request.user)
    if not sub_activa:
        messages.info(request,
                      'Necesitas un plan de promociones activo. Elige uno y '
                      'empezamos con tu primera promoción.')
        return redirect(reverse('detalle_servicio', kwargs={'slug': 'promociones'}))

    plan = sub_activa.plan

    # Sin datos de negocio no hay snapshot para el equipo: se los pedimos primero.
    if not DatosNegocio.objects.filter(usuario=request.user).exists():
        return redirect('promociones:suscribir_promocion', plan_id=plan.id)

    if not _puede_crear_promocion(request.user, plan):
        messages.warning(request,
                         'Has alcanzado el límite de promociones de tu plan actual. '
                         'Puedes ampliar tu plan para crear más.')
        return redirect('promociones:mis_promociones')

    tipos = [t for t in plan.get_tipos_permitidos_list()
             if t in ('evento', 'negocio', 'ninguno')] or ['ninguno']
    datos_negocio = DatosNegocio.objects.filter(usuario=request.user).first()

    if request.method == 'POST':
        tipo = request.POST.get('tipo_formulario', plan.tipo_formulario)
        if tipo not in tipos:
            tipo = tipos[0]
        form = PromocionSolicitudForm(request.POST, request.FILES, tipo=tipo,
                                      datos_negocio=datos_negocio, plan=plan)
        if form.is_valid():
            with transaction.atomic():
                solicitud = form.save(commit=False)
                solicitud.usuario = request.user
                solicitud.plan = plan
                solicitud.suscripcion = sub_activa
                solicitud.estado = 'pendiente'
                solicitud.save()
            messages.success(request,
                             '¡Solicitud enviada! Nuestro equipo comenzará a trabajar en ella.')
            return redirect('promociones:solicitud_enviada', solicitud_id=solicitud.id)
    else:
        # El tipo se puede cambiar por GET (?tipo=negocio) para recargar la
        # página con los campos correctos sin JavaScript complejo.
        tipo_actual = request.GET.get('tipo', plan.tipo_formulario)
        if tipo_actual not in tipos:
            tipo_actual = plan.tipo_formulario if plan.tipo_formulario in tipos else tipos[0]
        form = PromocionSolicitudForm(tipo=tipo_actual, datos_negocio=datos_negocio,
                                      plan=plan)

    tipo_render = form.tipo if request.method == 'GET' else request.POST.get(
        'tipo_formulario', plan.tipo_formulario)
    return render(request, 'promociones/crear_promocion.html', {
        'modo': 'adicional',
        'plan': plan,
        'plan_actual': plan,
        'tipos_permitidos': tipos,
        'promociones_restantes': _promociones_restantes(request.user, plan),
        'tipo_inicial': tipo_render,
        'form': form,
        'titulo_pagina': 'Crear Nueva Promoción',
    })

# ==============================================================================
# Paso 4 — Confirmación
# ==============================================================================
@login_required(login_url=URL_REGISTRO)
def solicitud_enviada(request, solicitud_id):
    """Pantalla de confirmación: todo quedó en manos del equipo administrativo."""
    solicitud = get_object_or_404(
        SolicitudPromocion.objects.select_related('plan', 'plan__servicio'),
        id=solicitud_id, usuario=request.user)
    return render(request, 'promociones/solicitud_enviada.html', {
        'solicitud': solicitud,
        'titulo_pagina': 'Solicitud enviada',
    })

@login_required(login_url=URL_REGISTRO)
def cliente_aprobar_diseno(request, pk):
    """El cliente aprueba el diseño de su tarjeta (pasa a 'aprobada').

    Solo puede hacerlo el dueño de la solicitud y solo si está en 'disenando'
    con una tarjeta borrador asociada.
    """
    solicitud = get_object_or_404(
        SolicitudPromocion.objects.select_related('promocion_creada'),
        pk=pk, usuario=request.user)

    if request.method != 'POST':
        return redirect('promociones:panel_promociones')

    if solicitud.estado != 'disenando' or not solicitud.promocion_creada:
        messages.warning(request, 'Esta solicitud no está lista para aprobar.')
        return redirect('promociones:panel_promociones')

    solicitud.estado = 'aprobada'
    solicitud.save(update_fields=['estado'])
    messages.success(request,
                     '¡Gracias! Has aprobado el diseño. El equipo lo publicará en breve.')
    return redirect('promociones:panel_promociones')
# ==============================================================================
# Tarjetas públicas
# ==============================================================================
def ver_promocion(request, slug):
    """Página pública de una tarjeta publicada (la que se comparte en redes).
    
        Las tarjetas NO publicadas (borrador) solo son visibles para su dueño y
        para el equipo (VISTA PREVIA), nunca para el público general.
        """
    promocion = get_object_or_404(Promocion, slug=slug)
    vista_previa = False
    
    if not promocion.publicada:
        usuario = request.user
        try:
            dueno_id = promocion.solicitud.usuario_id
        except SolicitudPromocion.DoesNotExist:
            dueno_id = None
        permitido = usuario.is_authenticated and (
            usuario.is_staff or usuario.id == dueno_id)
        if not permitido:
            raise Http404('Promoción no disponible.')
        vista_previa = True
    else:
        # Contador de visitas atómico (solo cuenta el público)
        Promocion.objects.filter(pk=promocion.pk).update(vistas=F('vistas') + 1)
    
    return render(request, 'promociones/ver_promocion.html', {
        'promocion': promocion,
        'vista_previa': vista_previa,
    })

def listado_publicadas(request):
    """Landing del servicio: todas las promociones publicadas."""
    promociones = Promocion.objects.filter(publicada=True)
    return render(request, 'promociones/listado_publicadas.html', {
        'promociones': promociones,
        'titulo_pagina': 'Promociones',
    })

# ==============================================================================
# Panel del equipo administrativo (staff)
# ==============================================================================
@staff_member_required
def admin_solicitudes(request):
    """Bandeja de solicitudes para el equipo, con filtros por estado y búsqueda."""
    estado = request.GET.get('estado', '')
    busqueda = request.GET.get('q', '').strip()

    qs = (SolicitudPromocion.objects
          .select_related('usuario', 'plan', 'plan__servicio', 'promocion_creada'))

    if estado in dict(SolicitudPromocion.ESTADOS):
        qs = qs.filter(estado=estado)

    if busqueda:
        qs = qs.filter(
            Q(usuario__username__icontains=busqueda) |
            Q(usuario__email__icontains=busqueda) |
            Q(titulo__icontains=busqueda) |
            Q(plan__nombre__icontains=busqueda)
        )

    conteos = {codigo: SolicitudPromocion.objects.filter(estado=codigo).count()
               for codigo, _ in SolicitudPromocion.ESTADOS}

    # Lista (codigo, nombre, total) lista para iterar en la plantilla
    estados_conteo = [(codigo, nombre, conteos[codigo])
                      for codigo, nombre in SolicitudPromocion.ESTADOS]

    return render(request, 'promociones/admin_solicitudes.html', {
        'solicitudes': qs,
        'estado_actual': estado,
        'estados': SolicitudPromocion.ESTADOS,
        'estados_conteo': estados_conteo,
        'conteos': conteos,
        'busqueda': busqueda,
    })

@staff_member_required
def admin_solicitud_detalle(request, pk):
    """Detalle completo de una solicitud con las acciones del equipo."""
    solicitud = get_object_or_404(
        SolicitudPromocion.objects
        .select_related('usuario', 'plan', 'plan__servicio', 'promocion_creada',
                        'suscripcion', 'plantilla'),
        pk=pk)

    estado_form = AdminCambiarEstadoForm(instance=solicitud)
    
    # Formulario de la tarjeta: creación (sin tarjeta) o edición (tarjeta existente)
    if solicitud.promocion_creada:
        promo_form = AdminPromocionForm(instance=solicitud.promocion_creada,
                                            solicitud=solicitud)
    else:
        promo_form = AdminPromocionForm(solicitud=solicitud)
    
    return render(request, 'promociones/admin_solicitud_detalle.html', {
        'solicitud': solicitud,
        'estado_form': estado_form,
        'promo_form': promo_form,
        'pasos_flujo': _pasos_flujo(solicitud),
    })

@staff_member_required
def admin_cambiar_estado(request, pk):
    """Cambia el estado de una solicitud y guarda notas internas."""
    solicitud = get_object_or_404(SolicitudPromocion, pk=pk)
    if request.method == 'POST':
        form = AdminCambiarEstadoForm(request.POST, instance=solicitud)
        if form.is_valid():
            form.save()
            messages.success(request, f'Solicitud #{solicitud.pk} actualizada '
                                      f'a "{solicitud.get_estado_display()}".')
        else:
            messages.error(request, 'No se pudo actualizar la solicitud. Revisa los datos.')
    return redirect('promociones:admin_solicitud_detalle', pk=pk)

# ------------------------------------------------------------------------------
# Helpers del panel staff
# ------------------------------------------------------------------------------
def _activar_suscripcion(sub):
    """Activa una suscripción fijando su ventana de vigencia (pago confirmado)."""
    sub.estado = 'activa'
    sub.fecha_inicio = timezone.localdate()
    sub.fecha_fin = timezone.localdate() + timedelta(days=sub.plan.vigencia_dias)
    sub.save()  # el save() del modelo cancela otras subs del mismo servicio

def _detalle_con_errores(request, solicitud, promo_form):
    """Re-renderiza el detalle del staff con los errores del formulario de tarjeta."""
    estado_form = AdminCambiarEstadoForm(instance=solicitud)
    return render(request, 'promociones/admin_solicitud_detalle.html', {
        'solicitud': solicitud,
        'estado_form': estado_form,
        'promo_form': promo_form,
        'pasos_flujo': _pasos_flujo(solicitud),
    })

def _pasos_flujo(solicitud):
    """Lista de pasos del flujo para el stepper del detalle:
    [{'codigo', 'nombre', 'hecho', 'actual'}, ...]."""
    nombres = dict(SolicitudPromocion.ESTADOS)
    idx = (ORDEN_FLUJO.index(solicitud.estado)
           if solicitud.estado in ORDEN_FLUJO else -1)
    return [{'codigo': codigo,
             'nombre': nombres.get(codigo, codigo),
             'hecho': i < idx,
             'actual': i == idx}
            for i, codigo in enumerate(ORDEN_FLUJO)]

# ------------------------------------------------------------------------------
# Crear / editar / publicar / despublicar la tarjeta (estados intermedios)
# ------------------------------------------------------------------------------
@staff_member_required
def admin_crear_tarjeta(request, pk):
    """Crea la tarjeta a partir de la solicitud, SIEMPRE en estado BORRADOR.

    Nunca publica automáticamente: la publicación es una acción explícita
    posterior (admin_publicar_tarjeta), de modo que la solicitud atraviesa
    los estados intermedios pendiente -> disenando -> aprobada -> publicada.

    Al crear la tarjeta, si la solicitud sigue 'pendiente' pasa a 'disenando'
    (el diseño ya existe, está a la espera de revisión/aprobación).
    Opcionalmente (checkbox) activa la suscripción al confirmar el pago.
    """
    solicitud = get_object_or_404(
        SolicitudPromocion.objects.select_related('suscripcion', 'plan'),
        pk=pk)

    if solicitud.promocion_creada:
        messages.info(request,
                      'Esta solicitud ya tiene una tarjeta. Usa "Guardar cambios" '
                      'para editarla.')
        return redirect('promociones:admin_solicitud_detalle', pk=pk)

    if solicitud.estado == 'rechazada':
        messages.error(request,
                       'La solicitud está rechazada: cambia su estado antes de '
                       'crear la tarjeta.')
        return redirect('promociones:admin_solicitud_detalle', pk=pk)

    if request.method == 'POST':
        form = AdminPromocionForm(request.POST, request.FILES, solicitud=solicitud)
        if form.is_valid():
            with transaction.atomic():
                promocion = form.save(commit=False)  # estado 'borrador', publicada False
                promocion.datos_extra = {
                    'solicitud_id': solicitud.pk,
                    'tipo': solicitud.tipo,
                    'negocio': solicitud.datos_negocio_snapshot,
                    'usuario': solicitud.usuario.username,
                }
                promocion.save()

                solicitud.promocion_creada = promocion
                if solicitud.estado == 'pendiente':
                    solicitud.estado = 'disenando'   # estado intermedio, NUNCA publicada
                solicitud.save()

                # Activación de la suscripción (confirmación de pago del cliente)
                if form.cleaned_data.get('activar_suscripcion') and solicitud.suscripcion:
                    _activar_suscripcion(solicitud.suscripcion)

            logger.info('Tarjeta borrador %s creada desde solicitud #%s',
                        promocion.pk, solicitud.pk)
            messages.success(
                request,
                f'Tarjeta "{promocion.titulo}" guardada como BORRADOR. '
                'Cuando el cliente apruebe el diseño, pulsa "Publicar tarjeta".')
            return redirect('promociones:admin_solicitud_detalle', pk=pk)

        return _detalle_con_errores(request, solicitud, form)

    return redirect('promociones:admin_solicitud_detalle', pk=pk)

@staff_member_required
def admin_editar_tarjeta(request, pk):
    """Guarda cambios en la tarjeta existente (borrador o publicada) sin tocar
    los estados: editar no publica ni despublica."""
    solicitud = get_object_or_404(
        SolicitudPromocion.objects.select_related('promocion_creada'), pk=pk)

    if not solicitud.promocion_creada:
        messages.info(request, 'Esta solicitud todavía no tiene tarjeta. Créala primero.')
        return redirect('promociones:admin_solicitud_detalle', pk=pk)

    if request.method == 'POST':
        form = AdminPromocionForm(request.POST, request.FILES,
                                  instance=solicitud.promocion_creada,
                                  solicitud=solicitud)
        if form.is_valid():
            form.save()  # conserva el estado actual de la tarjeta
            messages.success(request, 'Tarjeta actualizada.')
            return redirect('promociones:admin_solicitud_detalle', pk=pk)
        return _detalle_con_errores(request, solicitud, form)

    return redirect('promociones:admin_solicitud_detalle', pk=pk)

@staff_member_required
def admin_publicar_tarjeta(request, pk):
    """PUBLICA la tarjeta de la solicitud (acción explícita del equipo).

    Es el paso final del flujo: tarjeta -> 'publicada' y solicitud -> 'publicada'.
    Requiere que la tarjeta tenga la imagen final cargada.
    """
    solicitud = get_object_or_404(
        SolicitudPromocion.objects.select_related('promocion_creada'), pk=pk)
    tarjeta = solicitud.promocion_creada

    if request.method == 'POST' and tarjeta:
        if not tarjeta.imagen:
            messages.error(request,
                           'No se puede publicar sin la imagen final: edita la '
                           'tarjeta y súbela primero.')
            return redirect('promociones:admin_solicitud_detalle', pk=pk)

        with transaction.atomic():
            tarjeta.publicada = True
            tarjeta.estado = 'publicada'
            if not tarjeta.fecha_publicacion:
                tarjeta.fecha_publicacion = timezone.now()
            tarjeta.save()

            solicitud.estado = 'publicada'
            solicitud.save()

        logger.info('Tarjeta %s PUBLICADA (solicitud #%s)', tarjeta.pk, solicitud.pk)
        messages.success(request,
                         f'Tarjeta "{tarjeta.titulo}" PUBLICADA. Ya es visible en el '
                         'landing y en la bandeja del cliente.')
    return redirect('promociones:admin_solicitud_detalle', pk=pk)

@staff_member_required
def admin_despublicar_tarjeta(request, pk):
    """Vuelve la tarjeta a BORRADOR (p. ej. para corregir el diseño).

    La solicitud regresa a 'aprobada' para recompletar los estados intermedios
    cuando se vuelva a publicar.
    """
    solicitud = get_object_or_404(
        SolicitudPromocion.objects.select_related('promocion_creada'), pk=pk)
    tarjeta = solicitud.promocion_creada

    if request.method == 'POST' and tarjeta:
        with transaction.atomic():
            tarjeta.publicada = False
            tarjeta.estado = 'borrador'
            tarjeta.fecha_publicacion = None
            tarjeta.save()

            if solicitud.estado == 'publicada':
                solicitud.estado = 'aprobada'
                solicitud.save()

        messages.warning(request,
                         'Tarjeta despublicada (volver a borrador). Recuerda '
                         'publicarla de nuevo tras las correcciones.')
    return redirect('promociones:admin_solicitud_detalle', pk=pk)

@staff_member_required
def admin_activar_suscripcion(request, pk):
    """Activa la suscripción del cliente (confirmación de pago), sin esperar a
    crear/publicar la tarjeta."""
    solicitud = get_object_or_404(
        SolicitudPromocion.objects.select_related('suscripcion', 'suscripcion__plan'),
        pk=pk)

    if request.method == 'POST' and solicitud.suscripcion:
        sub = solicitud.suscripcion
        if sub.estado == 'activa':
            messages.info(request, 'La suscripción ya está activa.')
        else:
            _activar_suscripcion(sub)
            messages.success(request,
                             f'Suscripción de {sub.usuario.username} ACTIVADA hasta '
                             f'{sub.fecha_fin}.')
    return redirect('promociones:admin_solicitud_detalle', pk=pk)

# ------------------------------------------------------------------------------
# Compatibilidad: la antigua vista creaba y publicaba en un solo paso
# ------------------------------------------------------------------------------
@staff_member_required
def admin_publicar_promocion(request, pk):
    """(Compatibilidad) Antes creaba la tarjeta y la publicaba de golpe.
    Ahora el flujo va por estados: crea la tarjeta como borrador y publícala
    como paso explícito. Esta vista solo redirige al detalle.
    """
    messages.info(request,
                  'El flujo ahora respeta los estados intermedios: guarda la tarjeta '
                  'como borrador y publícala cuando esté aprobada.')
    return redirect('promociones:admin_solicitud_detalle', pk=pk)

@staff_member_required
def admin_publicar_promocion_old(request, pk):
    """Crea la tarjeta publicada a partir de la solicitud (paso final del equipo).

    Acciones realizadas (en una transacción):
        1. Crea la Promocion con la imagen final subida por el equipo.
        2. Vincula la tarjeta a la solicitud (promocion_creada) y la marca 'publicada'.
        3. Si el equipo lo indica, activa la suscripción del cliente fijando su
           fecha de vencimiento según la vigencia del plan.
    """
    solicitud = get_object_or_404(
        SolicitudPromocion.objects.select_related('suscripcion', 'plan'),
        pk=pk)

    if solicitud.promocion_creada:
        messages.info(request, 'Esta solicitud ya tiene una tarjeta publicada.')
        return redirect('promociones:admin_solicitud_detalle', pk=pk)

    if request.method == 'POST':
        form = AdminPromocionForm(request.POST, request.FILES, solicitud=solicitud)
        if form.is_valid():
            with transaction.atomic():
                promocion = form.save(commit=False)
                publicar = form.cleaned_data.get('publicada', True)
                print(publicar)
                promocion.publicada = publicar
                promocion.estado = 'publicada' if publicar else 'borrador'
                promocion.datos_extra = {
                    'solicitud_id': solicitud.pk,
                    'tipo': solicitud.tipo,
                    'negocio': solicitud.datos_negocio_snapshot,
                    'usuario': solicitud.usuario.username,
                }
                promocion.save()

                solicitud.promocion_creada = promocion
                if solicitud.metodo_creacion == 'ia':
                    solicitud.estado = 'disenando'
                else:
                    solicitud.estado = 'publicada'
                solicitud.save()

                # Activación de la suscripción (confirmación de pago por parte del equipo)
                if form.cleaned_data.get('activar_suscripcion') and solicitud.suscripcion:
                    sub = solicitud.suscripcion
                    sub.estado = 'activa'
                    sub.fecha_inicio = timezone.localdate()
                    sub.fecha_fin = (timezone.localdate()
                                     + timedelta(days=sub.plan.vigencia_dias))
                    sub.save()  # el save() del modelo cancela otras subs del mismo servicio

            messages.success(request,
                             f'Tarjeta "{promocion.titulo}" creada y solicitud actualizada.')
            return redirect('promociones:admin_solicitud_detalle', pk=pk)

        # Formulario inválido: re-render del detalle con los errores visibles
        estado_form = AdminCambiarEstadoForm(instance=solicitud)
        return render(request, 'promociones/admin_solicitud_detalle.html', {
            'solicitud': solicitud,
            'estado_form': estado_form,
            'promo_form': form,
        })

    return redirect('promociones:admin_solicitud_detalle', pk=pk)
