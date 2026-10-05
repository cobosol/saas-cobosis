from django.db import models
from django.utils.text import slugify
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User
#from clientes.models import 
from servicios.models import Plan, Suscripcion
import uuid

class TemplateCard(models.Model):
    CATEGORY_CHOICES = (
        ('evento', 'Evento'),
        ('invitacion', 'Invitación'),
        ('negocio', 'Negocio'),
        ('agradecimiento', 'Agradecimiento'),
        ('promocion', 'Promoción'),
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    thumbnail = models.ImageField(upload_to='templates/thumbnails/', blank=True, null=True)
    html_template = models.TextField(help_text="HTML con variables en {{ variable }}")
    css_template = models.TextField(blank=True, help_text="CSS personalizado")
    # Schema de campos dinámicos (JSON)
    fields_schema = models.JSONField(default=dict, help_text="Ej: {'fields': [{'name':'titulo','type':'text','label':'Título'}, ...]}")
    # Lista de variables permitidas (para validación)
    allowed_variables = models.JSONField(default=list, help_text="Lista de variables que pueden usarse en el HTML")

    def __str__(self):
        return self.name

TIPOS = [
        ('evento', 'Evento'),
        ('negocio', 'Negocio'),
    ]

class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    tipo = models.CharField(max_length=10, choices=TIPOS, default='evento')
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name_plural = "Categorías"

    def __str__(self):
        return self.nombre
    
    def promociones(self):
        return Promocion.objects.filter(categoria=self, estado='publicado').order_by('-prioridad', '-creado')

class Promocion(models.Model):
    ESTADOS = [
        ('pendiente',   'Pendiente'),          # recién creada por el cliente
        ('disenando',   'Diseñando'),          # admin/cobosis trabajando
        ('revision',    'En revisión'),        # IA generó, esperando OK del cliente
        ('aprobada',    'Aprobada por cliente'),
        ('activa',      'Publicada'),
        ('rechazada',   'Rechazada'),
        ('cancelada',   'Cancelada'),
    ]

    #cliente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='promociones')
    suscripcion = models.ForeignKey(Suscripcion, on_delete=models.CASCADE, related_name='promociones', null=True, blank=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, related_name='promociones')
    tipo = models.CharField(max_length=10, choices=TIPOS, default='evento')
    titulo = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)

    custom_data = models.JSONField(default=dict)
    descripcion = models.TextField(blank=True)
    enlace_accion = models.URLField(blank=True, null=True, help_text="Botón de WhatsApp, web, etc.")

    imagen_cliente = models.ImageField(upload_to='promociones/', null=True, blank=True, help_text="Imagen subida por el cliente (proporción 1:1.618)")
    html_tarjeta = models.TextField(blank=True, null=True, help_text="HTML con estilos de la tarjeta")
    template = models.ForeignKey(TemplateCard, on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Solo si modo='plantilla'")
    #generar_imagen_ia = models.BooleanField(default=False, help_text="True si el cliente quiere que le generemos la imagen")

    fecha_evento = models.DateTimeField()
    dias_evento = models.PositiveSmallIntegerField(default=1)
    lugar = models.CharField(max_length=200, blank=True)
    estado = models.CharField(max_length=10, choices=ESTADOS, default='pendiente')

    prioridad = models.PositiveSmallIntegerField(default=0) # se copia del plan del cliente
    destacado = models.BooleanField(default=False, help_text="True si compró 'Visibilidad preferential'")
    permite_actualizar = models.BooleanField(default=False, help_text="True si es plan 'Promoción extendida'")
    
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)
    visits = models.PositiveIntegerField(default=0)
    rsvp_clicks = models.PositiveIntegerField(default=0)

    # Archivos generados por Cobosis (admin)
    imagen_generada = models.ImageField(
        upload_to='solicitudes_generadas/', null=True, blank=True
    )
    comentario_admin = models.TextField(blank=True)
    comentario_cliente = models.TextField(blank=True)

    class Meta:
        ordering = ['-destacado', '-prioridad', '-creado']  # los de mayor prioridad y más recientes primero

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.titulo)
            self.slug = f"{base_slug}-{uuid.uuid4().hex[:8]}"
        # Asignar prioridad según el plan del cliente (si no se ha forzado)
        if self.suscripcion.estado == 'activa':
            self.prioridad = self.suscripcion.plan.nivel_prioridad
        super().save(*args, **kwargs)

    def __str__(self):
        return self.titulo

    @property
    def esta_vigente(self):
        from django.utils import timezone
        return self.estado == 'publicado' and self.fecha_evento > timezone.now()
    
class RSVP(models.Model):
    promotion = models.ForeignKey(Promocion, on_delete=models.CASCADE, related_name='rsvps')
    name = models.CharField(max_length=100)
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.promotion.title}"
    
class SolicitudPromocion(models.Model):
    ESTADO = [('pendiente','Pendiente'), ('disenando','Diseñando'), ('activa','Activa'), ('rechazada','Rechazada')]
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='solicitudes_promocion')
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=10, choices=TIPOS, default='evento')
    datos_recopilados = models.TextField(default='')

    # ---- Modo de creación ----
    MODO = [
                    ('plantilla',  'Desde plantilla'),
                    ('imagen',     'Imagen propia'),
                    ('ia',         'Generada con IA (Cobosis)'),
            ]
    modo = models.CharField(max_length=20, choices=MODO, default='plantilla')
        
    # NUEVOS CAMPOS DE IMAGEN
    generar_imagen_ia = models.BooleanField(default=False, help_text="True si el cliente quiere que le generemos la imagen")
    imagen_subida = models.ImageField(upload_to='solicitudes_promociones/', null=True, blank=True, help_text="Imagen subida por el cliente (proporción 1:1.618)")
    
    estado = models.CharField(max_length=20, choices=ESTADO, default='pendiente')
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    promocion_creada = models.ForeignKey(Promocion, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self): return f"Solicitud de {self.usuario.username}"
