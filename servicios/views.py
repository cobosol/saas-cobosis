"""
Vistas de la aplicación 'servicios' (VERSACIÓN CORREGIDA para engranar con promociones).

Cambios respecto a la versión anterior:
    1. procesar_suscripcion ya no depende del decorador login_required: si el
       usuario no está autenticado redirige al REGISTRO con ?next=... para que,
       tras registrarse, continúe pidiendo el plan que quería (paso 2 del flujo).
    2. El plan de promociones de pago ahora redirige CON el plan_id:
       redirect('promociones:suscribir_promocion', plan_id=plan.id).
       Antes se perdía el plan y el flujo se rompía.
    3. El plan gratuito de promociones también pasa por el flujo (datos del
       negocio + primera promoción), aunque la suscripción se activa al momento.
    4. Se añade el import de Q que faltaba para panel_suscripciones.
"""
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from urllib.parse import quote

from clientes.models import User  # noqa: F401
from servicios.models import Servicio, Suscripcion

from .models import Plan, Servicio


def servicios(request):
    servicios = Servicio.objects.filter(activo=True)
    return render(request, 'servicios/servicios.html', {'servicios': servicios})


def detalle_servicio(request, slug):
    """Paso 1 del flujo: el usuario revisa los planes del servicio."""
    servicio = get_object_or_404(Servicio, slug=slug, activo=True)
    planes = servicio.planes.filter(activo=True).order_by('orden')
    return render(request, 'servicios/detalle_servicio.html', {
        'servicio': servicio,
        'planes': planes,
    })


def _url_registro(next_url=None):
    """URL del formulario de registro preservando el destino."""
    if not next_url:
        return reverse('registro')
    return f'{reverse("registro")}?next={quote(next_url)}'


def procesar_suscripcion(request, plan_id):
    """Paso 2 del flujo: el usuario solicita un plan concreto.

    - Anónimo      -> formulario de registro (con ?next= para volver aquí).
    - Autenticado  -> según el servicio:
        * promociones (pago o gratis) -> flujo de promociones:
            suscribir_promocion (datos del negocio) -> primera_promocion.
        * gestiona (gratis)   -> activación inmediata + panel de gestiona.
        * gestiona (pago)     -> crea la suscripción 'solicitada' y avisa al panel.
    """
    plan = get_object_or_404(Plan, id=plan_id, activo=True)
    servicio_slug = plan.servicio.slug

    # ---- Paso 2: si no está registrado, mostrar el formulario de registro ----
    if not request.user.is_authenticated:
        return redirect(_url_registro(request.get_full_path()))

    # 1. VALIDACIÓN PLAN PRUEBA (solo una vez en la vida)
    if plan.precio == 0:
        ya_tuvo_prueba = Suscripcion.objects.filter(
            usuario=request.user, plan=plan).exists()
        if ya_tuvo_prueba:
            messages.error(request,
                           'Ya has utilizado el Plan Prueba gratuito anteriormente. '
                           'Debes elegir un plan de pago.')
            return redirect('inicio')

    # 2. PLANES GRATUITOS: activación inmediata
    if plan.precio == 0:
        if servicio_slug == 'promociones':
            # La suscripción gratuita se activa, pero el cliente aún necesita
            # enviar los datos del negocio y su primera promoción.
            Suscripcion.objects.get_or_create(
                usuario=request.user, plan=plan,
                defaults={'estado': 'activa'})
            return redirect('promociones:suscribir_promocion', plan_id=plan.id)

        if servicio_slug == 'gestiona':
            # El método save() del modelo cancela la suscripción anterior automáticamente
            Suscripcion.objects.create(
                usuario=request.user,
                plan=plan,
                estado='activa',
            )
            messages.success(request,
                             f'¡Felicidades! Tu plan "{plan.nombre}" ha sido activado.')
            return redirect('gestiona_panel')

        Suscripcion.objects.create(usuario=request.user, plan=plan, estado='activa')
        messages.success(request, f'¡Felicidades! Tu plan "{plan.nombre}" ha sido activado.')
        return redirect('panel_cliente')

    # 3. PLANES DE PAGO: solicitud + derivación al flujo correspondiente
    if servicio_slug == 'promociones':
        # Paso 2.1: formulario de suscripción con datos del negocio (paso 2.1 del flujo)
        return redirect('promociones:suscribir_promocion', plan_id=plan.id)

    if servicio_slug == 'gestiona':
        ya_solicitada = Suscripcion.objects.filter(
            usuario=request.user, plan=plan, estado='solicitada').exists()
        if ya_solicitada:
            messages.info(request, 'Ya tienes una solicitud pendiente para este plan.')
        else:
            Suscripcion.objects.create(usuario=request.user, plan=plan,
                                       estado='solicitada')
            messages.success(request,
                             f'¡Solicitud recibida para el plan "{plan.nombre}"! '
                             'Nos pondremos en contacto contigo.')
        return redirect('panel_cliente')

    # Otros servicios futuros
    Suscripcion.objects.get_or_create(
        usuario=request.user, plan=plan,
        defaults={'estado': 'solicitada'})
    messages.success(request,
                     f'¡Solicitud recibida para el plan "{plan.nombre}"! '
                     'Nos pondremos en contacto contigo.')
    return redirect('panel_cliente')


# ==============================================================================
# Panel administrativo de suscripciones (sin cambios funcionales)
# ==============================================================================
@staff_member_required
def panel_suscripciones(request):
    estado = request.GET.get('estado', 'solicitada')
    busqueda = request.GET.get('q', '').strip()

    qs = Suscripcion.objects.select_related('usuario', 'plan', 'plan__servicio')

    if estado in dict(Suscripcion.ESTADO):
        qs = qs.filter(estado=estado)

    if busqueda:
        qs = qs.filter(
            Q(usuario__username__icontains=busqueda) |
            Q(usuario__email__icontains=busqueda) |
            Q(plan__nombre__icontains=busqueda) |
            Q(plan__servicio__nombre__icontains=busqueda)
        )

    conteos = {
        'solicitada': Suscripcion.objects.filter(estado='solicitada').count(),
        'activa':     Suscripcion.objects.filter(estado='activa').count(),
        'vencida':    Suscripcion.objects.filter(estado='vencida').count(),
        'cancelada':  Suscripcion.objects.filter(estado='cancelada').count(),
    }

    return render(request, 'servicios/panel.html', {
        'suscripciones': qs,
        'estado_actual': estado,
        'estados': Suscripcion.ESTADO,
        'conteos': conteos,
        'busqueda': busqueda,
    })


@staff_member_required
def aprobar_suscripcion(request, pk):
    """Activa la suscripción (el equipo la usa tras confirmar el pago)."""
    sub = get_object_or_404(Suscripcion, pk=pk)
    if request.method == 'POST':
        sub.estado = 'activa'
        sub.fecha_inicio = timezone.localdate()
        sub.fecha_fin = timezone.localdate() + timedelta(days=sub.plan.vigencia_dias)
        sub.save()
        messages.success(request, f'Suscripción de "{sub.usuario.username}" aprobada.')
    return redirect(request.META.get('HTTP_REFERER', 'panel_suscripciones'))


@staff_member_required
def denegar_suscripcion(request, pk):
    sub = get_object_or_404(Suscripcion, pk=pk)
    if request.method == 'POST':
        sub.estado = 'cancelada'
        sub.activo = False
        sub.save(update_fields=['estado', 'activo'])
        messages.warning(request, f'Suscripción de "{sub.usuario.username}" denegada.')
    return redirect(request.META.get('HTTP_REFERER', 'panel_suscripciones'))
