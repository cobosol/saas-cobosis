from django.db import models

# Create your models here.
from django.db import models
from django.urls import reverse

class Servicio(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, help_text="Usado para la URL (ej: promociones)")
    descripcion_corta = models.CharField(max_length=255, help_text="Texto breve para la tarjeta en la home")
    descripcion_larga = models.TextField(help_text="Información general del servicio para su página de detalle")
    icono = models.CharField(max_length=50, default="fas fa-rocket", help_text="Clase de Font Awesome para el icono")
    activo = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0, help_text="Orden de aparición en la página principal")

    class Meta:
        ordering = ['orden']
        verbose_name = "Servicio"
        verbose_name_plural = "Servicios"

    def __str__(self):
        return self.nombre

    def get_absolute_url(self):
        return reverse('detalle_servicio', kwargs={'slug': self.slug})


class Plan(models.Model):
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE, related_name='planes')
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(help_text="Ej: Incluye enlace directo, diseño de tarjeta...")
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    vigencia_dias = models.PositiveIntegerField(default=30, help_text="Duración de la suscripción en días")
    
    destacado = models.BooleanField(default=False, help_text="Marcar si es el plan más popular")
    activo = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0)
    
    # Campos para Gestiona
    max_variables = models.PositiveIntegerField(default=3, help_text="Cantidad máxima de variables a extraer (Ej: 3, 5, 10)")
    max_extracciones = models.PositiveIntegerField(default=10, help_text="Límite de extracciones totales. Usar 0 para ilimitado.")
    dias_retencion = models.PositiveIntegerField(default=30, help_text="Días que se guardan los datos. Ej: 30, 365")
    variables_ajustables = models.BooleanField(default=False, help_text="Marcar si el usuario puede definir sus propias variables")

    # Campos para Promociones (Tu idea de prioridad)
    nivel_prioridad = models.PositiveSmallIntegerField(default=0, help_text="Prioridad en el listado (0 es normal, >0 es preferencial)")
    tipo_formulario = models.CharField(max_length=20, choices=[('evento','Evento'),('negocio','Negocio'),('ninguno','Genérico')], default='ninguno')

    class Meta:
        ordering = ['orden']
        verbose_name = "Plan"
        verbose_name_plural = "Planes"

    def __str__(self):
        return f"{self.nombre} ({self.servicio.nombre})"