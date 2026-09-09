from django.contrib import admin
from .models import Categoria, Promocion, SolicitudPromocion, TemplateCard

@admin.register(TemplateCard)
class TemplateCardAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'category')
    fields = ('name', 'slug', 'category', 'thumbnail', 'html_template', 'css_template', 'fields_schema', 'allowed_variables')
    prepopulated_fields = {'slug': ('name',)}


class CategoriaAdmin(admin.ModelAdmin):
    pass

class PromocionAdmin(admin.ModelAdmin):
    pass

class SolicitudPAdmin(admin.ModelAdmin):
    pass

admin.site.register(Categoria, CategoriaAdmin)
admin.site.register(Promocion, PromocionAdmin)
admin.site.register(SolicitudPromocion, SolicitudPAdmin)
