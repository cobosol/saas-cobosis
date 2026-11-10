from django.core.management.base import BaseCommand
from promociones.models import PlantillaPromocion

EVENTO_HTML = """
<div class="promo-card promo-evento">
  <div class="promo-card__badge">¡Estás invitado!</div>
  <h1 class="promo-card__title">{{ titulo }}</h1>
  <p class="promo-card__date">
    {{ fecha }}{% if hora %} · {{ hora }}{% endif %}
  </p>
  <p class="promo-card__place">📍 {{ lugar }}</p>
  {% if descripcion %}<p class="promo-card__desc">{{ descripcion }}</p>{% endif %}
  {% if enlace_accion %}
    <a class="promo-card__cta" href="{{ enlace_accion }}">Más información</a>
  {% endif %}
</div>
<style>
  .promo-evento {
    max-width: 480px; margin: 0 auto; padding: 2.5rem 2rem; text-align: center;
    background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
    border-radius: 24px; box-shadow: 0 20px 40px rgba(0,0,0,.15);
    font-family: 'Playfair Display', Georgia, serif; color: #422006;
  }
  .promo-evento .promo-card__badge {
    display: inline-block; background: #92400e; color: #fff;
    padding: .35rem 1rem; border-radius: 999px; font-size: .8rem;
    letter-spacing: .1em; text-transform: uppercase; margin-bottom: 1.2rem;
  }
  .promo-evento .promo-card__title {
    font-size: 2.2rem; margin: 0 0 1rem; line-height: 1.15;
  }
  .promo-evento .promo-card__date {
    font-size: 1.15rem; font-weight: 600; margin: 0 0 .4rem;
  }
  .promo-evento .promo-card__place { font-size: 1rem; margin: 0 0 1.2rem; }
  .promo-evento .promo-card__desc {
    font-size: .95rem; line-height: 1.5; margin: 0 0 1.5rem; opacity: .85;
  }
  .promo-evento .promo-card__cta {
    display: inline-block; background: #92400e; color: #fff;
    text-decoration: none; padding: .75rem 1.75rem; border-radius: 999px;
    font-weight: 600; letter-spacing: .02em;
  }
  .promo-evento .promo-card__cta:hover { background: #78350f; }
</style>
"""

EVENTO_SCHEMA = {
    "fields": [
        {"name": "titulo", "type": "text", "label": "Título del evento",
         "required": True, "maxlength": 80},
        {"name": "fecha", "type": "date", "label": "Fecha del evento",
         "required": True},
        {"name": "hora", "type": "time", "label": "Hora", "required": False},
        {"name": "lugar", "type": "text", "label": "Lugar",
         "required": True, "maxlength": 120},
        {"name": "descripcion", "type": "textarea", "label": "Descripción",
         "required": False, "maxlength": 300},
        {"name": "enlace_accion", "type": "url",
         "label": "Enlace (ej. Google Maps, formulario)", "required": False},
    ]
}

NEGOCIO_HTML = """
<div class="promo-card promo-negocio">
  <div class="promo-card__header" style="background: {{ color_primario|default:'#2563eb' }};">
    <span class="promo-card__tag">Oferta especial</span>
    <h2 class="promo-card__title">{{ titulo }}</h2>
  </div>
  <div class="promo-card__body">
    <p class="promo-card__desc">{{ descripcion }}</p>
    {% if telefono %}
      <p class="promo-card__phone">📞 {{ telefono }}</p>
    {% endif %}
    {% if enlace_accion %}
      <a class="promo-card__cta" href="{{ enlace_accion }}">Aprovechar oferta</a>
    {% endif %}
  </div>
</div>
<style>
  .promo-negocio {
    max-width: 420px; margin: 0 auto; border-radius: 20px; overflow: hidden;
    box-shadow: 0 20px 40px rgba(0,0,0,.12); font-family: 'Inter', sans-serif;
    background: #fff;
  }
  .promo-negocio .promo-card__header {
    padding: 2rem 1.5rem; color: #fff; text-align: center;
  }
  .promo-negocio .promo-card__tag {
    display: inline-block; background: rgba(255,255,255,.25);
    padding: .3rem .9rem; border-radius: 999px; font-size: .75rem;
    letter-spacing: .1em; text-transform: uppercase; margin-bottom: .9rem;
  }
  .promo-negocio .promo-card__title {
    font-size: 1.6rem; margin: 0; font-weight: 800; line-height: 1.2;
  }
  .promo-negocio .promo-card__body { padding: 1.5rem; color: #1f2937; }
  .promo-negocio .promo-card__desc {
    font-size: 1rem; line-height: 1.6; margin: 0 0 1rem;
  }
  .promo-negocio .promo-card__phone {
    font-weight: 600; margin: 0 0 1rem; color: #374151;
  }
  .promo-negocio .promo-card__cta {
    display: block; text-align: center; background: #111827; color: #fff;
    text-decoration: none; padding: .9rem 1.5rem; border-radius: 12px;
    font-weight: 700;
  }
  .promo-negocio .promo-card__cta:hover { background: #1f2937; }
</style>
"""

NEGOCIO_SCHEMA = {
    "fields": [
        {"name": "titulo", "type": "text", "label": "Título de la oferta",
         "required": True, "maxlength": 80},
        {"name": "descripcion", "type": "textarea", "label": "Descripción de la oferta",
         "required": True, "maxlength": 300},
        {"name": "telefono", "type": "text", "label": "Teléfono de contacto",
         "required": False, "maxlength": 30},
        {"name": "color_primario", "type": "color", "label": "Color principal",
         "required": False},
        {"name": "enlace_accion", "type": "url", "label": "Enlace de acción",
         "required": False},
    ]
}


class Command(BaseCommand):
    help = 'Crea las plantillas HTML de ejemplo (evento y negocio).'

    def handle(self, *args, **options):
        PlantillaPromocion.objects.update_or_create(
            nombre='Invitación de cumpleaños',
            categoria='evento',
            defaults={
                'descripcion': 'Tarjeta elegante tipo invitación para eventos personales.',
                'html_content': EVENTO_HTML,
                'fields_schema': EVENTO_SCHEMA,
                'activa': True,
            },
        )
        PlantillaPromocion.objects.update_or_create(
            nombre='Oferta de negocio',
            categoria='negocio',
            defaults={
                'descripcion': 'Tarjeta moderna para promociones comerciales con CTA.',
                'html_content': NEGOCIO_HTML,
                'fields_schema': NEGOCIO_SCHEMA,
                'activa': True,
            },
        )
        self.stdout.write(self.style.SUCCESS('Plantillas HTML de ejemplo creadas.'))