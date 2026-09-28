"""
Formularios del módulo de promociones.

Flujo de suscripción (pasos 2 -> 3 del negocio):
    1. DatosNegocioForm        -> paso 2/2.1: datos del negocio y detalles de contacto.
    2. PromocionSolicitudForm  -> paso 3: formulario de la (primera) promoción.
                                  Los campos cambian según el tipo (evento/negocio/genérico),
                                  admite subir imagen propia o pedir diseño con IA.

Panel administrativo:
    3. AdminCambiarEstadoForm  -> cambiar estado / notas internas.
    4. AdminPromocionForm      -> crear la tarjeta publicada a partir de la solicitud.

Notas de validación:
    - La imagen subida debe tener proporción 1 : 1.618 (se tolera ±2%).
    - Si el cliente marca "diseñar con IA", el brief es obligatorio y la imagen opcional.
    - Si no marca IA, la imagen es obligatoria.
"""
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import DatosNegocio, PlantillaPromocion, Promocion, SolicitudPromocion

# Clases Tailwind reutilizables para los widgets
INPUT_CLS = ('w-full p-2 border border-gray-300 rounded-lg '
             'focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none')


# ==============================================================================
# PASO 2 / 2.1 — Datos del negocio
# ==============================================================================
class DatosNegocioForm(forms.ModelForm):
    """Formulario de suscripción: datos del negocio y detalles de contacto."""

    class Meta:
        model = DatosNegocio
        fields = [
            'nombre_negocio', 'rubro', 'telefono_whatsapp', 'descripcion',
            'direccion', 'sitio_web', 'instagram', 'facebook',
        ]
        widgets = {
            'nombre_negocio': forms.TextInput(attrs={'class': INPUT_CLS,
                                                     'placeholder': 'Ej: Restaurante La Fogata'}),
            'rubro': forms.TextInput(attrs={'class': INPUT_CLS,
                                            'placeholder': 'Ej: Comida rápida'}),
            'telefono_whatsapp': forms.TextInput(attrs={'class': INPUT_CLS,
                                                        'placeholder': 'Ej: +53 5XXXXXXX'}),
            'descripcion': forms.Textarea(attrs={'class': INPUT_CLS, 'rows': 3,
                                                 'placeholder': 'Breve reseña de lo que ofrece tu negocio'}),
            'direccion': forms.TextInput(attrs={'class': INPUT_CLS,
                                                'placeholder': 'Dirección del negocio (opcional)'}),
            'sitio_web': forms.URLInput(attrs={'class': INPUT_CLS,
                                               'placeholder': 'https://... (opcional)'}),
            'instagram': forms.TextInput(attrs={'class': INPUT_CLS,
                                                'placeholder': 'Usuario de Instagram sin @ (opcional)'}),
            'facebook': forms.TextInput(attrs={'class': INPUT_CLS,
                                               'placeholder': 'Página de Facebook (opcional)'}),
        }
        labels = {
            'nombre_negocio': 'Nombre del negocio *',
            'rubro': 'Rubro / giro *',
            'telefono_whatsapp': 'Teléfono / WhatsApp *',
            'descripcion': 'Descripción general *',
            'direccion': 'Dirección',
            'sitio_web': 'Sitio web',
            'instagram': 'Instagram',
            'facebook': 'Facebook',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nombre_negocio'].required = True
        self.fields['rubro'].required = True
        self.fields['telefono_whatsapp'].required = True
        self.fields['descripcion'].required = True


# ==============================================================================
# PASO 3 — Formulario de la promoción (primera promoción o adicional)
# ==============================================================================
class PromocionSolicitudForm(forms.ModelForm):
    """Formulario de la promoción solicitada.

    Los campos concretos se construyen dinámicamente según `tipo`:
        evento  -> titulo, fecha_evento, hora_evento, lugar_evento, info_evento
        negocio -> titulo, descripcion_negocio, telefono_contacto
        ninguno -> titulo, descripcion_generica

    Campos comunes: enlace_accion, plantilla (opcional), generar_con_ia,
    brief_ia (si IA) e imagen_subida (si no IA).

    En save() los campos dinámicos se guardan en SolicitudPromocion.datos con la
    estructura: {'negocio': {...}, 'promocion': {...}}.
    """

    class Meta:
        model = SolicitudPromocion
        fields = ['plantilla', 'generar_con_ia', 'brief_ia', 'imagen_subida']
        widgets = {
            'plantilla': forms.Select(attrs={'class': INPUT_CLS}),
            'generar_con_ia': forms.CheckboxInput(attrs={'class': 'w-5 h-5 rounded text-blue-600 focus:ring-blue-500'}),
            'brief_ia': forms.Textarea(attrs={'class': INPUT_CLS, 'rows': 5,
                                              'placeholder': 'Describe tu evento/negocio, colores preferidos, textos obligatorios, etc.'}),
            'imagen_subida': forms.ClearableFileInput(attrs={'class': INPUT_CLS, 'accept': 'image/*'}),
        }
        labels = {
            'plantilla': 'Plantilla base (opcional)',
            'generar_con_ia': 'Deseo que el equipo diseñe mi tarjeta con Inteligencia Artificial',
            'brief_ia': 'Cuéntanos qué quieres',
            'imagen_subida': 'Sube tu propia imagen (proporción 1 : 1.618)',
        }
        

    def __init__(self, *args, tipo='ninguno', datos_negocio=None, plan=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tipo = tipo if tipo in ('evento', 'negocio', 'ninguno') else 'ninguno'
        self.datos_negocio = datos_negocio
        self.plan = plan
        self.fields['enlace_accion'] = forms.CharField(
                        label='Enlace de acción (opcional)', required=False,
                        widget=forms.URLInput(attrs={'class': INPUT_CLS, 
                                                   'placeholder': 'https://... enlace del botón (opcional)'}))

        # ---------- Campos dinámicos según el tipo ----------
        if self.tipo == 'evento':
            self.fields['titulo'] = forms.CharField(
                label='Nombre o título del evento *', max_length=200,
                widget=forms.TextInput(attrs={'class': INPUT_CLS,
                                              'placeholder': 'Ej: Fiesta de Cumpleaños de Ana'}))
            self.fields['fecha_evento'] = forms.DateField(
                label='Fecha del evento *',
                widget=forms.DateInput(attrs={'type': 'date', 'class': INPUT_CLS}))
            self.fields['hora_evento'] = forms.TimeField(
                label='Hora del evento *', required=False,
                widget=forms.TimeInput(attrs={'type': 'time', 'class': INPUT_CLS}))
            self.fields['lugar_evento'] = forms.CharField(
                label='Lugar del evento *', max_length=200,
                widget=forms.TextInput(attrs={'class': INPUT_CLS,
                                              'placeholder': 'Dirección o nombre del salón'}))
            self.fields['info_evento'] = forms.CharField(
                label='Información detallada', required=False,
                widget=forms.Textarea(attrs={'class': INPUT_CLS, 'rows': 3,
                                             'placeholder': 'Detalles adicionales del evento'}))
        elif self.tipo == 'negocio':
            self.fields['titulo'] = forms.CharField(
                label='Título de la oferta o promoción *', max_length=200,
                widget=forms.TextInput(attrs={'class': INPUT_CLS,
                                              'placeholder': 'Ej: 2x1 en pizzas todos los viernes'}))
            self.fields['descripcion_negocio'] = forms.CharField(
                label='Descripción de la promoción *',
                widget=forms.Textarea(attrs={'class': INPUT_CLS, 'rows': 3,
                                             'placeholder': 'Detalla la oferta que quieres anunciar'}))
            self.fields['telefono_contacto'] = forms.CharField(
                label='Teléfono / WhatsApp que aparecerá en la tarjeta', max_length=30, required=False,
                widget=forms.TextInput(attrs={'class': INPUT_CLS,
                                              'placeholder': 'Si lo dejas vacío usamos el del negocio'}),
                initial=getattr(datos_negocio, 'telefono_whatsapp', None))
        else:  # ninguno (genérico)
            self.fields['titulo'] = forms.CharField(
                label='Título de la promoción *', max_length=200,
                widget=forms.TextInput(attrs={'class': INPUT_CLS}))
            self.fields['descripcion_generica'] = forms.CharField(
                label='Descripción *',
                widget=forms.Textarea(attrs={'class': INPUT_CLS, 'rows': 3}))

        # ---------- Plantillas disponibles para este tipo ----------
        qs_plantillas = PlantillaPromocion.objects.filter(activa=True, categoria=self.tipo)
        if not qs_plantillas.exists():
            del self.fields['plantilla']

    # ------------------------------ Validaciones ------------------------------
    def clean_imagen_subida(self):
        img = self.cleaned_data.get('imagen_subida')
        if not img:
            return img
        if img.size > 5 * 1024 * 1024:
            raise ValidationError('La imagen no puede superar los 5 MB.')
        return img

    def clean(self):
        cleaned = super().clean()
        generar_ia = cleaned.get('generar_con_ia')
        imagen = cleaned.get('imagen_subida')
        brief = cleaned.get('brief_ia')

        if generar_ia and not (brief or '').strip():
            self.add_error('brief_ia', 'Describe tu idea en el brief para que el equipo '
                                       '(y la IA) sepan qué diseñar.')
        if not generar_ia and not imagen:
            self.add_error('imagen_subida',
                           'Debes subir una imagen o marcar la opción de diseño con IA.')
        if imagen and not generar_ia:
            self._validar_proporcion(imagen)
        return cleaned

    @staticmethod
    def _validar_proporcion(imagen):
        """Valida la proporción 1 : 1.618 (altura/ancho entre 1.58 y 1.65)."""
        from PIL import Image
        try:
            with Image.open(imagen) as im:
                ancho, alto = im.size
        except Exception:
            raise ValidationError('No se pudo leer la imagen. Verifica que sea un '
                                  'archivo de imagen válido (JPG, PNG, WEBP).')
        if ancho == 0:
            raise ValidationError('La imagen es inválida.')
        ratio = alto / ancho
        if ratio < 1.58 or ratio > 1.65:
            raise ValidationError(
                f'La proporción de la imagen es 1:{ratio:.2f} (ancho {ancho}px, alto {alto}px). '
                f'Debe ser 1:1.618, por ejemplo 600x970 px.')

    # ------------------------------ Guardado ---------------------------------
    def build_datos(self):
        """Construye el JSON `datos` de la solicitud con la información completa."""
        datos = {
            'promocion': {},
            'negocio': self.datos_negocio.como_snapshot() if self.datos_negocio else {},
            'plan': {
                'id': self.plan.id,
                'nombre': self.plan.nombre,
                'precio': str(self.plan.precio),
                'vigencia_dias': self.plan.vigencia_dias,
                'max_promociones': self.plan.max_promociones,
            } if self.plan else {},
        }

        promocion = {}
        if self.tipo == 'evento':
            fecha = self.cleaned_data.get('fecha_evento')
            promocion = {
                'titulo': self.cleaned_data.get('titulo'),
                'fecha_evento': fecha.isoformat() if fecha else None,
                'hora_evento': self.cleaned_data.get('hora_evento').strftime('%H:%M')
                               if self.cleaned_data.get('hora_evento') else None,
                'lugar_evento': self.cleaned_data.get('lugar_evento'),
                'info_evento': self.cleaned_data.get('info_evento', ''),
            }
        elif self.tipo == 'negocio':
            promocion = {
                'titulo': self.cleaned_data.get('titulo'),
                'descripcion_negocio': self.cleaned_data.get('descripcion_negocio'),
                'telefono_contacto': self.cleaned_data.get('telefono_contacto', ''),
            }
        else:
            promocion = {
                'titulo': self.cleaned_data.get('titulo'),
                'descripcion_generica': self.cleaned_data.get('descripcion_generica'),
            }
        datos['promocion'] = promocion
        return datos

    def save(self, commit=True):
        instancia = super().save(commit=False)
        instancia.tipo = self.tipo
        instancia.titulo = self.cleaned_data.get('titulo', '')[:200]
        instancia.datos = self.build_datos()

        if instancia.generar_con_ia:
            instancia.metodo_creacion = 'ia'
        elif getattr(self, 'cleaned_data', {}).get('plantilla'):
            instancia.metodo_creacion = 'plantilla'
        else:
            instancia.metodo_creacion = 'propia'

        if commit:
            instancia.save()
        return instancia


# ==============================================================================
# Panel administrativo
# ==============================================================================
class AdminCambiarEstadoForm(forms.ModelForm):
    """Cambio de estado + notas internas desde el panel del equipo."""

    class Meta:
        model = SolicitudPromocion
        fields = ['estado', 'notas_admin']
        widgets = {
            'estado': forms.Select(attrs={'class': INPUT_CLS}),
            'notas_admin': forms.Textarea(attrs={'class': INPUT_CLS, 'rows': 3}),
        }
        labels = {'estado': 'Nuevo estado', 'notas_admin': 'Notas internas (no las ve el cliente)'}


class AdminPromocionForm(forms.ModelForm):
    """Formulario para crear la tarjeta publicada a partir de una solicitud."""

    activar_suscripcion = forms.BooleanField(
        required=False,
        initial=True,
        label='Activar la suscripción del cliente',
        help_text='Marca esta casilla al confirmar el pago: activa la suscripción '
                  'y fija su fecha de vencimiento según el plan.'
    )

    class Meta:
        model = Promocion
        fields = ['titulo', 'descripcion', 'imagen', 'fecha_evento', 'lugar',
                  'enlace_accion', 'publicada']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': INPUT_CLS}),
            'descripcion': forms.Textarea(attrs={'class': INPUT_CLS, 'rows': 3}),
            'imagen': forms.ClearableFileInput(attrs={'class': INPUT_CLS, 'accept': 'image/*'}),
            'fecha_evento': forms.DateTimeInput(attrs={'type': 'datetime-local',
                                                       'class': INPUT_CLS}),
            'lugar': forms.TextInput(attrs={'class': INPUT_CLS}),
            'enlace_accion': forms.URLInput(attrs={'class': INPUT_CLS}),
            'publicada': forms.CheckboxInput(
                attrs={'class': 'w-5 h-5 rounded text-green-600 focus:ring-green-500'}),
        }
        labels = {
            'titulo': 'Título de la tarjeta *',
            'descripcion': 'Descripción',
            'imagen': 'Imagen final de la tarjeta *',
            'fecha_evento': 'Fecha y hora del evento (si aplica)',
            'lugar': 'Lugar (si aplica)',
            'enlace_accion': 'Enlace de acción',
            'publicada': 'Publicar inmediatamente en el landing',
        }

    def __init__(self, *args, solicitud=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.solicitud = solicitud
        if solicitud:
            campos = solicitud.campos_promocion or {}
            negocio = solicitud.datos_negocio_snapshot or {}
            # Precarga con lo que envió el cliente para acelerar el trabajo del equipo
            if not self.is_bound:
                self.fields['titulo'].initial = solicitud.titulo or campos.get('titulo', '')
                self.fields['descripcion'].initial = (
                    campos.get('info_evento')
                    or campos.get('descripcion_negocio')
                    or campos.get('descripcion_generica')
                    or negocio.get('descripcion', '')
                )
                self.fields['lugar'].initial = (campos.get('lugar_evento')
                                                or negocio.get('direccion', ''))
                if solicitud.tipo == 'evento' and campos.get('fecha_evento'):
                    self.fields['fecha_evento'].initial = campos.get('fecha_evento')
                self.fields['enlace_accion'].initial = solicitud.enlace_accion or ''

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('publicada') and not cleaned.get('imagen'):
            self.add_error('imagen', 'Necesitas subir la imagen final para poder publicar.')
        return cleaned
