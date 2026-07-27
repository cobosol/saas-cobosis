from django.contrib import admin
from .models import Categoria, Promocion, SolicitudPromocion

class CategoriaAdmin(admin.ModelAdmin):
    pass

class PromocionAdmin(admin.ModelAdmin):
    pass

class SolicitudPAdmin(admin.ModelAdmin):
    pass

admin.site.register(Categoria, CategoriaAdmin)
admin.site.register(Promocion, PromocionAdmin)
admin.site.register(SolicitudPromocion, SolicitudPAdmin)
