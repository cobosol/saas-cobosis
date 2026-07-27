from django.urls import path
from .views import SignUpView, ProfileUpdate, EmailUpdate, Actualizar_perfil_admin
from django.contrib.auth import views as auth_views
from . import views
from .forms import CustomPasswordResetForm

urlpatterns = [
    path('signup/', SignUpView.as_view(), name = 'signup'),
    path('panel/', views.panel_cliente, name='panel_cliente'),
    path('profile/', ProfileUpdate.as_view(), name = 'profile'),
    path('profile/email/', EmailUpdate.as_view(), name = 'profile_email'),
    path('users_list/', views.users_list, name='users_list'),
    path('profile/editar/<int:pk>', Actualizar_perfil_admin.as_view(template_name = "registration/profile_actualizar_admin.html"), name='actualizar_perfil_admin'),

    path('registro/', views.registro, name='registro'),
    path('confirmacion-envio/', views.confirmacion_envio, name='confirmacion_envio'),
    path('activar/<uidb64>/<token>/', views.activar_cuenta, name='activar'),
    path('cuenta-activada/', views.cuenta_activada, name='cuenta_activada'),

    path('password_change/', auth_views.PasswordChangeView.as_view(template_name='registration/password_change.html'),name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(template_name='registration/password_change_done.html'),name='password_change_done'),


    path('password_reset/', 
         auth_views.PasswordResetView.as_view(
             form_class=CustomPasswordResetForm,
             template_name='registration/password_reset_form.html',
             email_template_name='registration/password_reset_email.txt',
             html_email_template_name='registration/password_reset_email.html',
             subject_template_name='registration/password_reset_subject.txt'
         ), 
         name='password_reset'),
    
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
             template_name='registration/password_reset_done.html'
         ), name='password_reset_done'),
    
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
             template_name='registration/password_reset_confirm.html'
         ), name='password_reset_confirm'),
    
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
             template_name='registration/password_reset_complete.html'
         ), name='password_reset_complete'),
]