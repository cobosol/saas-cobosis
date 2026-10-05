from django.core.exceptions import ImproperlyConfigured

CAPABILITIES_REGISTRY = {
    'can_customize_color': 'Permite cambiar colores de la tarjeta',
    'can_remove_logo': 'Permite quitar el logo de la plataforma',
    'can_rsvp': 'Permite recoger confirmaciones de asistencia',
    'can_analytics': 'Acceso a estadísticas detalladas',
    # Añadir nuevas capacidades aquí
}

def get_capabilities():
    return CAPABILITIES_REGISTRY

def check_plan_capability(plan, capability):
    """Verifica si un plan tiene una capacidad específica."""
    return plan.capabilities.get(capability, False)