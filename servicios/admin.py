from django.contrib import admin
from .models import Servicio, Plan

class ServicioAdmin(admin.ModelAdmin):
    pass

class PlanAdmin(admin.ModelAdmin):
    pass

admin.site.register(Servicio, ServicioAdmin)
admin.site.register(Plan, PlanAdmin)