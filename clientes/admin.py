from django.contrib import admin
from .models import PerfilCliente
from servicios.models import Suscripcion

class ClienteAdmin(admin.ModelAdmin):
    pass

class SuscripcionesAdmin(admin.ModelAdmin):
    pass

admin.site.register(PerfilCliente, ClienteAdmin)
admin.site.register(Suscripcion, SuscripcionesAdmin)
