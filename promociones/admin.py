"""
Registro de los modelos de promociones en el admin de Django.

El panel administrativo web (templates promociones/admin_*.html) es la
herramienta principal del equipo, pero el admin de Django es útil para
gestionar plantillas, revisar datos JSON y corregir estados puntualmente.
"""
from django.contrib import admin

from .models import DatosNegocio, PlantillaPromocion, Promocion, SolicitudPromocion


@admin.register(PlantillaPromocion)
class PlantillaPromocionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'activa')
    list_filter = ('categoria', 'activa')
    search_fields = ('nombre', 'descripcion')


@admin.register(Promocion)
class PromocionAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'estado', 'publicada', 'vistas', 'fecha_publicacion')
    list_filter = ('estado', 'publicada')
    search_fields = ('titulo', 'slug')
    readonly_fields = ('slug', 'vistas', 'creada_en')
    prepopulated_fields = {}  # el slug se genera automáticamente en save()


@admin.register(SolicitudPromocion)
class SolicitudPromocionAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'usuario', 'plan', 'tipo', 'metodo_creacion',
                    'estado', 'fecha_solicitud')
    list_filter = ('estado', 'tipo', 'metodo_creacion', 'plan__servicio')
    search_fields = ('titulo', 'usuario__username', 'usuario__email')
    autocomplete_fields = ('usuario', 'plan')
    readonly_fields = ('fecha_solicitud', 'fecha_actualizacion')


@admin.register(DatosNegocio)
class DatosNegocioAdmin(admin.ModelAdmin):
    list_display = ('nombre_negocio', 'usuario', 'rubro', 'telefono_whatsapp',
                    'fecha_actualizacion')
    search_fields = ('nombre_negocio', 'usuario__username', 'usuario__email')
    autocomplete_fields = ('usuario',)
