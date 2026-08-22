from django.db import models
from django.utils.text import slugify
from django.contrib.auth.models import User
#from clientes.models import 
from servicios.models import Plan, Suscripcion
import uuid

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
        ('pendiente', 'Pendiente'),
        ('publicado', 'Publicado'),
        ('vencido', 'Vencido'),
    ]
    
    cliente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='promociones')
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, related_name='promociones')
    tipo = models.CharField(max_length=10, choices=TIPOS, default='evento')
    titulo = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    descripcion = models.TextField()
    imagen = models.ImageField(upload_to='promociones/')
    fecha_evento = models.DateTimeField()
    lugar = models.CharField(max_length=200, blank=True)
    estado = models.CharField(max_length=10, choices=ESTADOS, default='pendiente')
    prioridad = models.PositiveSmallIntegerField(default=0) # se copia del plan del cliente
    destacado = models.BooleanField(default=False)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-prioridad', '-creado']  # los de mayor prioridad y más recientes primero

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.titulo)
            self.slug = f"{base_slug}-{uuid.uuid4().hex[:8]}"
        # Asignar prioridad según el plan del cliente (si no se ha forzado)
        if self.cliente_id:
            suscripcion_activa = Suscripcion.objects.filter(
                usuario=self.cliente, 
                plan__servicio__slug='promociones', 
                estado='activa'
            ).first()
            
            if suscripcion_activa:
                self.prioridad = suscripcion_activa.plan.nivel_prioridad
        super().save(*args, **kwargs)

    def __str__(self):
        return self.titulo
    
class SolicitudPromocion(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente de Contacto/Pago'),
        ('disenando', 'En Proceso de Diseño'),
        ('activa', 'Activa y Publicada'),
        ('rechazada', 'Rechazada/Cancelada'),
    ]
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='solicitudes_promocion')
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=10, choices=TIPOS, default='evento')
    datos_recopilados = models.TextField(default='', help_text="Guarda los datos como texto: 'titulo: X, fecha: Y'")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    promocion_creada = models.ForeignKey(Promocion, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Solicitud de {self.usuario.username} - {self.plan.nombre}"
