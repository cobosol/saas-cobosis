from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import now
from django.dispatch import receiver
from servicios.models import Plan
from django.db.models.signals import post_save
from django.utils import timezone
from datetime import timedelta

class PerfilCliente(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    cid = models.CharField(max_length=20, verbose_name = "Número de identidad", default='11111111111')
    avatar = models.ImageField(upload_to='profiles', null=True, blank=True, verbose_name = "Foto")
    bio = models.TextField(null=True, blank=True, verbose_name = "Biografía")
    link = models.URLField(max_length=200, null=True, blank=True, verbose_name = "Enlace")
    phone = models.CharField(max_length=15, null=True, blank = True,
                            help_text='', 
                            verbose_name = "Número de móvil")
    ws = models.CharField(max_length=15, null=True, blank = True, verbose_name = "Número para WhatsApp")
    
    # Special User
    reeup = models.CharField(max_length=20, unique=True, null=True, blank = True,
                            help_text='', 
                            verbose_name = "Código REEUP")
    nit = models.CharField(max_length=20, unique=True, null=True, blank = True,
                            help_text='', 
                            verbose_name = "Código NIT")
    address = models.CharField(max_length=100, null=True, blank = True, 
                            verbose_name = "Dirección oficial")
    agency = models.CharField(max_length=100, null=True, blank = True, 
                            verbose_name = "Agencia bancaria")
    contract = models.CharField(max_length=50, null=True, blank = True, 
                            verbose_name = "Número de contrato")
    class Meta:
        ordering = ['user']
        verbose_name = "Perfil"
        verbose_name_plural = "Perfiles"

    def __str__(self):
        return f'{self.user.first_name} {self.user.last_name}'

    @property
    def name(self):
        return self.user.first_name + ' ' + self.user.last_name
    
    @property
    def get_avatar_url(self):
        if self.avatar and hasattr(self.avatar, 'url'):
            return self.avatar.url 
        else:
            return "/static/img/Profile/pensativo.jpg"
        
@receiver(post_save, sender=User)
def ensure_profile_exists(sender, instance, **kwargs):
    if kwargs.get('created', False):
        PerfilCliente.objects.get_or_create(user=instance)

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
        # lógica para verificar si el plan sigue vigente
        return not self.fecha_fin or self.fecha_fin >= now().date()
    
    @property
    def dias_restantes(self):
        if self.fecha_fin > now().date():
            delta = self.fecha_fin - now().date()
            return delta.days 
        else:
            return 0

    def save(self, *args, **kwargs):
        # Si la suscripción se está marcando como 'activa'
        self.fecha_fin = timezone.now() + timedelta(days=self.plan.vigencia_dias)
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