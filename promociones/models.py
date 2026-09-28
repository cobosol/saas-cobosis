from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from clientes.models import User
from servicios.models import Plan, Suscripcion

"""
Modelos de la aplicación 'promociones'.

Piezas centrales del módulo:
    - DatosNegocio:      información del negocio del cliente (reutilizable en todas sus solicitudes).
    - PlantillaPromocion: plantillas base que puede usar el equipo de diseño / IA.
    - Promocion:         la tarjeta publicada en el landing (URL pública /p/<slug>/).
    - SolicitudPromocion: entidad central del flujo. Une usuario + plan + datos del negocio +
                          datos de la promoción solicitada. Es lo que el equipo administrativo
                          recibe para contactar al cliente (pago / activación / diseño).
"""
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from clientes.models import User
from servicios.models import Plan, Suscripcion


# ==============================================================================
# Datos del negocio del cliente
# ==============================================================================
class DatosNegocio(models.Model):
    """Datos generales del negocio del cliente.

    Se capturan en el paso 2 del flujo de suscripción a promociones y se
    reutilizan como 'initial' en solicitudes futuras, además de copiarse como
    snapshot (JSON) dentro de cada SolicitudPromocion para que el equipo
    administrativo vea exactamente lo que el cliente envió.
    """

    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='datos_negocio')
    nombre_negocio = models.CharField('Nombre del negocio', max_length=200)
    rubro = models.CharField('Rubro / giro', max_length=120, blank=True,
                             help_text="Ej: Comida rápida, Peluquería, Eventos")
    telefono_whatsapp = models.CharField('Teléfono / WhatsApp', max_length=30, blank=True)
    descripcion = models.TextField('Descripción del negocio', blank=True,
                                   help_text='Breve reseña de lo que ofrece el negocio')
    direccion = models.CharField('Dirección', max_length=255, blank=True)
    sitio_web = models.URLField('Sitio web', blank=True)
    instagram = models.CharField('Instagram', max_length=100, blank=True,
                                 help_text='Usuario sin @')
    facebook = models.CharField('Facebook', max_length=200, blank=True,
                                help_text='Nombre de la página o URL')
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Datos de negocio'
        verbose_name_plural = 'Datos de negocios'

    def __str__(self):
        return f'Negocio de {self.usuario.username}: {self.nombre_negocio}'

    def como_snapshot(self):
        """Devuelve los datos como dict para guardarlos en SolicitudPromocion.datos."""
        return {
            'nombre_negocio': self.nombre_negocio,
            'rubro': self.rubro,
            'telefono_whatsapp': self.telefono_whatsapp,
            'descripcion': self.descripcion,
            'direccion': self.direccion,
            'sitio_web': self.sitio_web,
            'instagram': self.instagram,
            'facebook': self.facebook,
        }


# ==============================================================================
# Plantillas de promoción (para diseño desde plantilla o base para la IA)
# ==============================================================================
class PlantillaPromocion(models.Model):
    """Plantilla base de tarjeta.

    fields_schema permite describir campos dinámicos, por ejemplo:
        {
            "fields": [
                {"name": "nombre_cumpleanero", "type": "text", "label": "Nombre del cumpleañero", "required": true},
                {"name": "fecha", "type": "date", "label": "Fecha del evento", "required": true}
            ]
        }
    El equipo administrativo puede usar esta información (o el brief) para
    diseñar la tarjeta manualmente o alimentar al generador con IA.
    """

    CATEGORIAS = [
        ('evento', 'Evento'),
        ('negocio', 'Negocio'),
        ('ninguno', 'Genérico'),
    ]

    nombre = models.CharField('Nombre de la plantilla', max_length=150)
    categoria = models.CharField('Categoría', max_length=20, choices=CATEGORIAS, default='ninguno')
    descripcion = models.TextField('Descripción', blank=True)
    fields_schema = models.JSONField(
        'Esquema de campos',
        default=dict,
        blank=True,
        help_text='JSON con la lista de campos dinámicos de la plantilla'
    )
    imagen_ejemplo = models.ImageField('Imagen de ejemplo', upload_to='promociones/plantillas/',
                                       blank=True, null=True)
    activa = models.BooleanField('Activa', default=True)

    class Meta:
        verbose_name = 'Plantilla de promoción'
        verbose_name_plural = 'Plantillas de promoción'
        ordering = ['categoria', 'nombre']

    def __str__(self):
        return f'{self.nombre} ({self.get_categoria_display()})'

    def get_campos(self):
        """Devuelve la lista de campos definidos en fields_schema."""
        if not self.fields_schema:
            return []
        return self.fields_schema.get('fields', [])


# ==============================================================================
# Tarjeta publicada en el landing
# ==============================================================================
class Promocion(models.Model):
    """La promoción publicada (tarjeta visible en el landing de la plataforma).

    Se crea desde el panel administrativo a partir de una SolicitudPromocion
    cuando el diseño está terminado y aprobado.
    """

    ESTADOS = [
        ('borrador', 'Borrador'),
        ('publicada', 'Publicada'),
        ('inactiva', 'Inactiva'),
    ]

    titulo = models.CharField('Título', max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True,
                            help_text='Se genera automáticamente. URL pública: /p/<slug>/')
    descripcion = models.TextField('Descripción', blank=True)
    imagen = models.ImageField('Imagen final', upload_to='promociones/publicadas/%Y/%m/',
                               blank=True, null=True)
    fecha_evento = models.DateTimeField('Fecha del evento', null=True, blank=True)
    lugar = models.CharField('Lugar', max_length=200, blank=True)
    enlace_accion = models.URLField('Enlace de acción (botón)', blank=True)
    datos_extra = models.JSONField('Datos extra', default=dict, blank=True,
                                   help_text='Información adicional de la solicitud original')
    estado = models.CharField('Estado', max_length=20, choices=ESTADOS, default='borrador')
    publicada = models.BooleanField('Publicada', default=False)
    fecha_publicacion = models.DateTimeField('Fecha de publicación', null=True, blank=True)
    vistas = models.PositiveIntegerField('Visitas', default=0)
    creada_en = models.DateTimeField('Creada', auto_now_add=True, null=True)

    class Meta:
        verbose_name = 'Promoción'
        verbose_name_plural = 'Promociones'
        ordering = ['-fecha_publicacion', '-creada_en']

    def __str__(self):
        return self.titulo

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._generar_slug_unico()
        # Sincroniza flags de conveniencia
        if self.publicada and not self.fecha_publicacion:
            self.fecha_publicacion = timezone.now()
        if self.estado == 'publicada':
            self.publicada = True
        super().save(*args, **kwargs)

    def _generar_slug_unico(self):
        base = slugify(self.titulo)[:200] or 'promocion'
        slug = base
        n = 2
        while Promocion.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f'{base}-{n}'
            n += 1
        return slug

    def get_absolute_url(self):
        return reverse('promociones:ver_promocion', kwargs={'slug': self.slug})

    @property
    def esta_publicada(self):
        return self.publicada and self.estado == 'publicada'


# ==============================================================================
# Solicitud de promoción (entidad central del flujo)
# ==============================================================================
class SolicitudPromocion(models.Model):
    """Solicitud de una promoción hecha por un cliente asociada a un plan.

    Estados (compatibles con Plan.permitir_mas_promociones en servicios.models):
        pendiente  -> recién creada, el equipo debe contactar al cliente (pago/activación)
        disenando  -> el equipo está diseñando la tarjeta
        aprobada   -> el cliente aprobó el diseño
        publicada  -> la tarjeta ya está publicada (promocion_creada)
        rechazada  -> solicitud cancelada / rechazada
    """

    ESTADOS = [
        ('pendiente', 'Pendiente de contacto/pago'),
        ('disenando', 'En proceso de diseño'),
        ('aprobada', 'Aprobada por el cliente'),
        ('publicada', 'Publicada'),
        ('rechazada', 'Rechazada/Cancelada'),
    ]

    METODOS_CREACION = [
        ('plantilla', 'Desde plantilla'),
        ('ia', 'Generada con IA'),
        ('propia', 'Imagen propia del cliente'),
    ]

    # Relaciones
    usuario = models.ForeignKey(User, on_delete=models.CASCADE,
                                related_name='solicitudes_promocion',
                                verbose_name='Cliente')
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='solicitudes_promocion',
                             verbose_name='Plan contratado')
    suscripcion = models.ForeignKey(Suscripcion, on_delete=models.SET_NULL,
                                    related_name='solicitudes_promocion',
                                    null=True, blank=True, verbose_name='Suscripción asociada')
    plantilla = models.ForeignKey(PlantillaPromocion, on_delete=models.SET_NULL,
                                  related_name='solicitudes', null=True, blank=True,
                                  verbose_name='Plantilla solicitada')

    # Contenido de la promoción
    tipo = models.CharField('Tipo de promoción', max_length=20,
                            choices=[('evento', 'Evento'), ('negocio', 'Negocio'),
                                     ('ninguno', 'Genérico')],
                            default='ninguno')
    titulo = models.CharField('Título de la promoción', max_length=200, null=True)
    datos = models.JSONField('Datos enviados por el cliente', default=dict, blank=True,
                             help_text='Snapshot: datos del negocio + campos específicos del tipo')
    enlace_accion = models.URLField('Enlace de acción (botón de la tarjeta)', blank=True, null=True)
    imagen_subida = models.ImageField('Imagen de referencia subida por el cliente',
                                      upload_to='promociones/solicitudes/%Y/%m/',
                                      blank=True, null=True)
    generar_con_ia = models.BooleanField('Diseñar con IA', default=False)
    brief_ia = models.TextField('Brief para el diseño con IA', blank=True)
    metodo_creacion = models.CharField('Método de creación', max_length=20,
                                       choices=METODOS_CREACION, default='propia')

    # Estados y control administrativo
    estado = models.CharField('Estado', max_length=20, choices=ESTADOS, default='pendiente')
    notas_admin = models.TextField('Notas internas del equipo', blank=True)
    promocion_creada = models.OneToOneField(Promocion, on_delete=models.SET_NULL,
                                            related_name='solicitud', null=True, blank=True,
                                            verbose_name='Promoción publicada')
    fecha_solicitud = models.DateTimeField('Fecha de solicitud', auto_now_add=True)
    fecha_actualizacion = models.DateTimeField('Última actualización', auto_now=True)

    class Meta:
        verbose_name = 'Solicitud de promoción'
        verbose_name_plural = 'Solicitudes de promoción'
        ordering = ['-fecha_solicitud']

    def __str__(self):
        return f'#{self.pk} {self.titulo} ({self.usuario.username} - {self.plan.nombre})'

    # ------------------------------- helpers ---------------------------------
    @property
    def en_proceso(self):
        """True mientras la solicitud aún no tenga tarjeta publicada ni esté rechazada."""
        return self.estado in ('pendiente', 'disenando', 'aprobada')

    @property
    def datos_negocio_snapshot(self):
        """Datos del negocio capturados en la suscripción (dict o {})."""
        return (self.datos or {}).get('negocio', {})

    @property
    def campos_promocion(self):
        """Campos específicos del tipo de promoción guardados en el JSON."""
        return (self.datos or {}).get('promocion', {})

    def get_url_publica(self):
        if self.promocion_creada:
            return self.promocion_creada.get_absolute_url()
        return None
