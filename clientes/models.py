from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import now
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.utils import timezone
from datetime import timedelta

class PerfilCliente(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
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
