from django import forms
from django.utils import timezone
from .models import SolicitudPromocion, Promocion
"""class PromotionForm(forms.ModelForm):
    
    class Meta:
        model = Promocion
        fields = ['titulo', 'descripcion', 'imagen', 'fecha_evento', 'lugar', 'estado']
        widgets = {
            'fecha_evento': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'descripcion': forms.Textarea(attrs={'rows': 4}),
            'estado': forms.Select(choices=Promocion.ESTADOS),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Los campos dinámicos (custom_data) no se tocan aquí, 
        # porque se editan directamente como JSON en el admin, 
        # o se dejan de lado en la edición simple por MVP.
        # Si quieres mostrarlos en edición, tendrías que renderizarlos aparte.

class PromotionStepForm(forms.ModelForm):
    
    class Meta:
        model = Promocion
        fields = ['titulo', 'descripcion', 'imagen', 'fecha_evento', 'lugar']
        
        widgets = {
            'fecha_evento': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'descripcion': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, template, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.template = template
        # Limpiar los campos extra que se agregarán dinámicamente
        schema = template.fields_schema.get('fields', [])
        for field in schema:
            field_name = field['name']
            field_type = field.get('type', 'text')
            label = field.get('label', field_name)
            required = field.get('required', False)
            initial = field.get('default', '')

            if field_type == 'text':
                self.fields[field_name] = forms.CharField(label=label, required=required, initial=initial)
            elif field_type == 'textarea':
                self.fields[field_name] = forms.CharField(widget=forms.Textarea, label=label, required=required, initial=initial)
            elif field_type == 'date':
                self.fields[field_name] = forms.DateField(label=label, required=required, initial=initial, widget=forms.DateInput(attrs={'type': 'date'}))
            elif field_type == 'datetime':
                self.fields[field_name] = forms.DateTimeField(label=label, required=required, initial=initial, widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}))
            elif field_type == 'url':
                self.fields[field_name] = forms.URLField(label=label, required=required, initial=initial)
            elif field_type == 'email':
                self.fields[field_name] = forms.EmailField(label=label, required=required, initial=initial)

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Guardar campos dinámicos en custom_data (JSON)
        custom_data = {}
        for field_name in self.fields:
            if field_name not in ['titulo', 'descripcion', 'imagen', 'fecha_evento', 'lugar']:
                custom_data[field_name] = self.cleaned_data.get(field_name)
        instance.custom_data = custom_data
        if commit:
            instance.save()
        return instance
"""

class BaseSolicitudForm(forms.ModelForm):
    class Meta:
        model = SolicitudPromocion
        fields = ['titulo'] if False else []   # no exponemos campos directos


class SolicitudPlantillaForm(forms.Form):
    titulo = forms.CharField(max_length=200)
    descripcion = forms.CharField(widget=forms.Textarea, required=False)
    fecha_evento = forms.DateTimeField(required=False, initial=timezone.now)
    lugar = forms.CharField(max_length=200, required=False)
    enlace_accion = forms.URLField(required=False)
    imagen_referencia = forms.ImageField(required=False)

    def __init__(self, *args, template=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.template = template
        # Cargar campos dinámicos desde fields_schema
        if template:
            schema = template.fields_schema or {}
            for campo in schema.get('fields', []):
                name = campo['name']
                tipo = campo.get('type', 'text')
                label = campo.get('label', name)
                required = campo.get('required', False)

                if tipo == 'text':
                    self.fields[name] = forms.CharField(label=label, required=required)
                elif tipo == 'textarea':
                    self.fields[name] = forms.CharField(
                        label=label, required=required, widget=forms.Textarea
                    )
                elif tipo == 'date':
                    self.fields[name] = forms.DateField(
                        label=label, required=required,
                        widget=forms.DateInput(attrs={'type': 'date'})
                    )
                elif tipo == 'image':
                    self.fields[name] = forms.ImageField(label=label, required=required)
                elif tipo == 'url':
                    self.fields[name] = forms.URLField(label=label, required=required)


class SolicitudImagenForm(forms.ModelForm):
    tipo = forms.ChoiceField(choices=[('evento', 'Evento'), ('negocio', 'Negocio')])

    class Meta:
        model = SolicitudPromocion
        fields = ['imagen_subida']
        widgets = {
            'imagen_subida': forms.ClearableFileInput(attrs={'accept': 'image/*'})
        }
        labels = {'imagen_subida': 'Imagen (proporción 1:1.618)'}

    titulo = forms.CharField(max_length=200)
    descripcion = forms.CharField(widget=forms.Textarea, required=False)
    fecha_evento = forms.DateTimeField(required=False)
    lugar = forms.CharField(max_length=200, required=False)
    enlace_accion = forms.URLField(required=False)

    def clean_imagen_subida(self):
        img = self.cleaned_data.get('imagen_subida')
        if not img:
            raise forms.ValidationError('Debes subir una imagen.')
        if img.size > 5 * 1024 * 1024:
            raise forms.ValidationError('La imagen no puede superar 5 MB.')
        return img


class SolicitudIAForm(forms.Form):
    tipo = forms.ChoiceField(choices=[('evento', 'Evento'), ('negocio', 'Negocio')])
    titulo = forms.CharField(max_length=200)
    brief = forms.CharField(
        label='Cuéntanos qué quieres',
        widget=forms.Textarea(attrs={'rows': 5}),
        help_text='Describe el evento/negocio, colores preferidos, textos obligatorios, etc.'
    )
    fecha_evento = forms.DateTimeField(required=False)
    lugar = forms.CharField(max_length=200, required=False)
    enlace_accion = forms.URLField(required=False)
    referencia = forms.ImageField(required=False, label='Imagen de referencia (opcional)')