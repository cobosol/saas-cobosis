from django.contrib import admin
from .models import Servicio, Plan

class ServicioAdmin(admin.ModelAdmin):
    pass

class PlanAdmin(admin.ModelAdmin):
    list_display = ('servicio', 'nombre', 'precio', 'vigencia_dias')
    list_filter = ('servicio', 'precio')
    search_fields = ('nombre', 'vigencia_dias')
    #autocomplete_fields = ('usuario', 'plan')
    #readonly_fields = ('fecha_solicitud', 'fecha_actualizacion')

admin.site.register(Servicio, ServicioAdmin)
admin.site.register(Plan, PlanAdmin)