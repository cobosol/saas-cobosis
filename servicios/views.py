from django.shortcuts import get_object_or_404, render
from .models import Servicio, Plan
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import redirect, get_object_or_404
from .models import Plan
from servicios.models import Suscripcion
from clientes.models import PerfilCliente

# (Tu vista pagina_principal aquí arriba...)
def servicios(request):
    servicios = Servicio.objects.filter(activo=True)

    return render(request, 'servicios/servicios.html', {'servicios':servicios,})

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

@login_required(login_url='/login/')
def procesar_suscripcion(request, plan_id):
    plan = get_object_or_404(Plan, id=plan_id, activo=True)
    
    # 1. VALIDACIÓN PLAN PRUEBA (Solo una vez en la vida)
    if plan.precio == 0:
        ya_tuvo_prueba = Suscripcion.objects.filter(
            usuario=request.user, 
            plan=plan
        ).exists()
        
        if ya_tuvo_prueba:
            messages.error(request, 'Ya has utilizado el Plan Prueba gratuito anteriormente. Debes elegir un plan de pago.')
            # Redirigir a la página de detalle de gestiona o a donde estaban los planes
            return redirect('detalle_gestiona') 

    # 2. LÓGICA PARA PLANES GRATUITOS (Activación inmediata)
    if plan.precio == 0:
        # El método save() del modelo se encargará de cancelar el anterior automáticamente
        fecha_fin = timezone.now() + timedelta(days=plan.vigencia_dias)
        
        nueva_sub = Suscripcion.objects.create(
            usuario=request.user,
            plan=plan,
            fecha_fin=fecha_fin,
            estado='activa' # Esto dispara la cancelación de la anterior
        )
        messages.success(request, f'¡Felicidades! Tu plan "{plan.nombre}" ha sido activado.')
        
        if plan.servicio.slug == 'gestiona':
            return redirect('gestiona_panel')
        elif plan.servicio.slug == 'promociones':
            return redirect('promociones_panel')
        return redirect('panel_cliente')
    
    # 3. LÓGICA PARA PLANES DE PAGO (Solicitud manual)
    else:
        if plan.servicio.slug == 'promociones':
            return redirect('suscribir_promocion')

        elif plan.servicio.slug == 'gestiona':
            # Verificar si ya tiene una solicitud pendiente para este plan
            ya_solicitada = Suscripcion.objects.filter(
                usuario=request.user, 
                plan=plan, 
                estado='solicitada'
            ).exists()
            
            if ya_solicitada:
                messages.info(request, 'Ya tienes una solicitud pendiente para este plan.')
            else:
                Suscripcion.objects.create(
                    usuario=request.user,
                    plan=plan,
                    estado='solicitada',
                    fecha_fin=timezone.now() + timedelta(days=plan.vigencia_dias)
                )
                messages.success(request, f'¡Solicitud recibida para el plan "{plan.nombre}"! Nos pondremos en contacto contigo.')
            
            return redirect('panel_cliente')