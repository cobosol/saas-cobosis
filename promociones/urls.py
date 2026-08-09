from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('', views.promociones, name='promociones'),
    path('crear/', views.crear_promocion, name='crear_promocion'),
    path('p/<uuid:slug>/', views.ver_promocion, name='ver_promocion'),
    path('promociones/mis-promociones/', views.mis_promociones, name='mis_promociones'),
]





