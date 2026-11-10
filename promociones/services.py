from django.template import Context, Template
from django.utils.safestring import mark_safe


def render_promocion_html(plantilla, datos: dict) -> str:
    """Renderiza el HTML de la plantilla con los datos del cliente.

    - El HTML base es responsabilidad del admin (confiable).
    - Los valores vienen del cliente y se escapan por autoescape.
    - Devuelve el resultado como SafeString para poder inyectarlo con {{ ...|safe }}.
    """
    template = Template(plantilla.html_content)
    css = plantilla.css_content or ''
    html = template.render(Context(datos, autoescape=True))
    return mark_safe(f'<style>{css}</style>{html}')