from django import forms
from .models import Promocion

class PromotionForm(forms.ModelForm):
    """
    Formulario ESTÁNDAR para EDICIÓN de promociones existentes.
    No genera campos dinámicos, solo los campos fijos del modelo.
    """
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
    """
    Formulario DINÁMICO para el PASO 2 de CREACIÓN.
    Genera inputs en tiempo real basados en el schema de la plantilla.
    """
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