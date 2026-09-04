# Create your models here.
from django.db import models
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from clientes.models import User

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
    #price_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    #price_yearly = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    vigencia_dias = models.PositiveIntegerField(default=30, help_text="Duración de la suscripción en días")
    
    destacado = models.BooleanField(default=False, help_text="Marcar si es el plan más popular")
    activo = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0)
    tipo_formulario = models.CharField(max_length=20, choices=[('evento','Evento'),('negocio','Negocio'),('ninguno','Genérico')], default='ninguno')

    # NUEVO: Límite de promociones permitidas por plan
    max_promociones = models.IntegerField(
        default=1,
        help_text='Número máximo de promociones permitidas para este plan (0 = ilimitadas)'
    )

    # NUEVO: Tipos de promociones permitidas (separados por coma)
    tipos_permitidos = models.CharField(
        max_length=50,
        default='evento',
        help_text='Tipos de formulario permitidos separados por coma: evento,negocio,ninguno',
        blank=True
    )
    
    # Campos para Gestiona
    max_variables = models.PositiveIntegerField(default=3, help_text="Cantidad máxima de variables a extraer (Ej: 3, 5, 10)")
    max_extracciones = models.PositiveIntegerField(default=10, help_text="Límite de extracciones totales. Usar 0 para ilimitado.")
    dias_retencion = models.PositiveIntegerField(default=30, help_text="Días que se guardan los datos. Ej: 30, 365")
    variables_ajustables = models.BooleanField(default=False, help_text="Marcar si el usuario puede definir sus propias variables")

    # Campos para Promociones (Tu idea de prioridad)
    nivel_prioridad = models.PositiveSmallIntegerField(default=0, help_text="Prioridad en el listado (0 es normal, >0 es preferencial)")
    
    class Meta:
        ordering = ['orden']
        verbose_name = "Plan"
        verbose_name_plural = "Planes"

    def __str__(self):
        return f"{self.nombre} ({self.servicio.nombre})"

    def get_tipos_permitidos_list(self):
        """Devuelve lista de tipos permitidos"""
        if not self.tipos_permitidos:
            return ['evento', 'negocio', 'ninguno']
        return [t.strip() for t in self.tipos_permitidos.split(',') if t.strip()]
    
    def permite_mas_promociones(self, usuario):
        from promociones.models import SolicitudPromocion
        
        """Verifica si el usuario puede crear más promociones con este plan"""
        if self.max_promociones == 0:  # Ilimitadas
            return True
        
        suscripciones_activas = Suscripcion.objects.filter(
            usuario=usuario,
            plan=self,
            estado__in=['activa', 'solicitada']
        ).count()
        
        if suscripciones_activas == 0:
            return True  # Primera suscripción
        
        promociones_creadas = SolicitudPromocion.objects.filter(
            usuario=usuario,
            plan=self,
            estado__in=['pendiente', 'disenando', 'aprobada', 'publicada']
        ).count()
        
        return promociones_creadas < self.max_promociones

class Suscripcion(models.Model):
    ESTADO = [
        ('solicitada', 'Solicitada'),
        ('activa', 'Activa'),
        ('vencida', 'Vencida'),
        ('cancelada', 'Cancelada'),
    ]
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='planes')
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='clientes')
    activo = models.BooleanField(default=True)
    fecha_inicio = models.DateField(auto_now=True)
    estado = models.CharField(max_length=20, choices=ESTADO, default='activa')
    fecha_fin = models.DateField(null=True, blank=True)
    #payment_id = models.CharField(max_length=255, blank=True, null=True)  # ID de pago (Stripe u otro)

    class Meta:
        ordering = ['-fecha_inicio']
        verbose_name = "Suscripción"
        verbose_name_plural = "Suscripciones"

    def __str__(self):
        if self.usuario:
            return f"{self.usuario.username}-{self.plan.nombre}({self.estado})"
        else:
            return f'{self.plan.nombre}'
    
    @property
    def vigente(self):
        from django.utils import timezone
        # lógica para verificar si el plan sigue vigente
        return not self.fecha_fin or self.fecha_fin >= timezone.localdate()
    
    @property
    def dias_restantes(self):
        if self.fecha_fin > timezone.localdate():
            delta = self.fecha_fin - timezone.localdate()
            return delta.days 
        else:
            return 0

    def save(self, *args, **kwargs):
        # Si la suscripción se está marcando como 'activa'
        self.fecha_fin = timezone.localdate() + timedelta(days=self.plan.vigencia_dias)
        if self.estado == 'activa':
            # Buscar otras suscripciones del mismo usuario y mismo servicio
            # que estén activas o solicitadas, excluyendo la actual
            otras_subs = Suscripcion.objects.filter(
                usuario=self.usuario,
                plan__servicio=self.plan.servicio,
                estado__in=['activa', 'solicitada']
            ).exclude(id=self.id)
            
            # Cancelar las anteriores
            for sub in otras_subs:
                sub.estado = 'cancelada'
                # Evitamos que dispare el save recursivamente cambiando el estado
                super(Suscripcion, sub).save(update_fields=['estado']) 

        super(Suscripcion, self).save(*args, **kwargs)