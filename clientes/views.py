from .models import Suscripcion
from typing import Any
from django.db.models.base import Model as Model
from django.db.models.query import QuerySet
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect
from django.contrib.auth.forms import UserCreationForm
from django.views.generic import CreateView
from django.urls import reverse_lazy
from django import forms
from .forms import UserCreationFormWithEmail
from django.views.generic.edit import UpdateView
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import PerfilCliente
from .forms import CustomPasswordResetForm, ProfileForm, UserCreationFormWithEmail, EmailForm
#Librerías para mensajes, algunos basados en views
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib.messages.views import SuccessMessageMixin 
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from .tokens import token_activacion
from saas_cobosis.settings import EMAIL_HOST_USER
from django.contrib.auth.views import PasswordResetView

# Instanciamos las vistas genéricas de Django 
#from django.views import View
from django.views.generic import ListView, DetailView 
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.urls import reverse


@login_required
def panel_cliente(request):
    # En views.py -> def panel_cliente
    suscripciones = Suscripcion.objects.filter(
        usuario=request.user, 
        estado__in=['activa', 'solicitada'] # Solo mostramos estas dos
    ).select_related('plan__servicio')
    servicios_activos = []
    for sub in suscripciones:
        servicios_activos.append(sub.plan.servicio)
    context = {'suscripciones':suscripciones,
               'servicios_activos': servicios_activos,}
    return render(request, 'clientes/panel_cliente.html', context)

class CustomPasswordResetView(PasswordResetView):
    form_class=CustomPasswordResetForm
    template_name='clientes/password_reset_form.html'
    email_template_name='clientes/password_reset_email.txt',
    html_email_template_name='clientes/password_reset_email.html',
    subject_template_name='clientes/password_reset_subject.txt'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Tu correo electrónico'
        })

def registro(request):
    if request.method == 'POST':
        try:
            form = UserCreationFormWithEmail(request.POST)
            if form.is_valid():
                usuario = form.save(commit=False)
                usuario.is_active = False  # Usuario inactivo hasta activación
                usuario.first_name = form.cleaned_data['first_name']
                usuario.last_name = form.cleaned_data['last_name']
                usuario.save()
            
                # Crear correo de activación
                asunto = 'Activa tu cuenta'
                html_content = render_to_string('clientes/activacion_cuenta.html', {
                    'usuario': usuario,
                    'dominio': request.META['HTTP_HOST'],
                    'uid': urlsafe_base64_encode(force_bytes(usuario.pk)),
                    'token': token_activacion.make_token(usuario),
                })
                email = EmailMultiAlternatives(
                    asunto,
                    "Por favor activa tu cuenta",
                    EMAIL_HOST_USER,
                    to=[usuario.email]
                )
                email.attach_alternative(html_content, "text/html")
                email.send()
                messages.success(request,"Correo de activación enviado con éxito")
                return redirect('confirmacion_envio')
            else:
                messages.error(request,"Error de validación de la form")
        except:
            messages.error('Error desconocido. Contacte con la administración')
    else:
        form = UserCreationFormWithEmail()
    return render(request, 'clientes/signup.html', {'form': form})

def activar_cuenta(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        usuario = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        usuario = None

    if usuario is not None and token_activacion.check_token(usuario, token):
        usuario.is_active = True
        usuario.save()
        login(request, usuario)
        return redirect('cuenta_activada')
    else: 
        return redirect('signup') #render(request, 'registration/activacion_invalida.html')        

def confirmacion_envio(request):
    return render(request, 'clientes/confirmacion_envio.html')        
    
def cuenta_activada(request):
    return render(request, 'clientes/confirmacion_activacion.html')

class SignUpView(CreateView):
    form_class = UserCreationFormWithEmail
    template_name = 'clientes/signup.html'

    def get_success_url(self):
        return reverse_lazy('login') + '?register'
    
    def get_form(self, form_class=None):
        form = super(SignUpView, self).get_form()
        form.fields['username'].widget = forms.TextInput(attrs={'class':'form-control mb-2', 'placeholder':'Nombre de usuario'})
        form.fields['first_name'].widget = forms.TextInput(attrs={'class':'form-control mb-2', 'placeholder':'Nombre'})
        form.fields['last_name'].widget = forms.TextInput(attrs={'class':'form-control mb-2', 'placeholder':'Apellidos'})
        form.fields['email'].widget = forms.EmailInput(attrs={'class':'form-control mb-2', 'placeholder':'Dirección de correo electrónico'})
        form.fields['password1'].widget = forms.PasswordInput(attrs={'class':'form-control mb-2', 'placeholder':'Contraseña'})
        form.fields['password2'].widget = forms.PasswordInput(attrs={'class':'form-control mb-2', 'placeholder':'Repita la contraseña'})
        form.fields['username'].label = ''
        form.fields['first_name'].label = ''
        form.fields['last_name'].label = ''
        form.fields['email'].label = ''
        form.fields['password1'].label = ''
        form.fields['password2'].label = ''
        return form    

@method_decorator(login_required, name='dispatch')
class ProfileUpdate(UpdateView):
    form_class = ProfileForm
    success_url = '/' #reverse_lazy('profile')
    success_message = "Se ha actualizado correctamente el perfil."
    template_name = 'clientes/profile_form.html'

    def get_object(self):
        try:
            return PerfilCliente.objects.get(user=self.request.user)
        except PerfilCliente.DoesNotExist:
            return PerfilCliente.objects.create(user=self.request.user)

@method_decorator(login_required, name='dispatch')
class EmailUpdate(UpdateView):
    form_class = EmailForm
    success_url = reverse_lazy('profile')
    template_name = 'clientes/profile_email_form.html'

    def get_object(self):
        return self.request.user
    
    def get_form(self, form_class=None):
        form = super(EmailUpdate, self).get_form()
        form.fields['email'].widget = forms.EmailInput(attrs={'class': 'form-control mb-2', 'placeholder':'Email'})
        return form
    

def users_list(request, template_name="clientes/users_list.html"):
    perfiles = PerfilCliente.objects.all().order_by('-user__date_joined')
    return render(request, template_name, locals())
    

class Actualizar_perfil_admin(SuccessMessageMixin, UpdateView):
    model = PerfilCliente
    fields = '__all_'
    success_message = "Se ha actualizado correctamente el perfil."

    def get_success_url(self):
        return reverse('users_list')