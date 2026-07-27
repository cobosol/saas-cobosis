from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('', views.gestiona_panel, name='gestiona_panel'),
    path('gestiona/', views.detalle_gestiona, name='detalle_gestiona'),
    path('procesar/', views.gestiona_procesar, name='gestiona_procesar'),
    path('exportar/', views.gestiona_exportar_excel, name='gestiona_exportar_excel'),
]
