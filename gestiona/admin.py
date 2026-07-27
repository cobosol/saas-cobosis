from django.contrib import admin
from .models import VariableUsuario, Extraccion

class VariableAdmin(admin.ModelAdmin):
    pass

class ExtraccionAdmin(admin.ModelAdmin):
    pass

admin.site.register(VariableUsuario, VariableAdmin)
admin.site.register(Extraccion, ExtraccionAdmin)