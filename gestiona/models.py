from django.db import models
from django.contrib.auth.models import User
from clientes.models import Suscripcion

# Modelo para guardar las variables fijas del usuario (Relación 1 a N)
class VariableUsuario(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='variables_gestiona')
    nombre = models.CharField(max_length=50, help_text="Ej: cliente, producto, cantidad")
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('usuario', 'nombre') # Evita variables duplicadas
        ordering = ['orden']

    def __str__(self):
        return self.nombre


# Modelo de Extracción modificado (Sin JSONField)
class Extraccion(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='extracciones')
    suscripcion = models.ForeignKey(Suscripcion, on_delete=models.CASCADE, related_name='extracciones', null=True, blank=True)
    texto_original = models.TextField()
    # Guardaremos los datos como texto plano. Ej: "cliente: Juan, producto: Camisa, cantidad: 2"
    datos_extraidos = models.TextField(default='') 
    variables_utilizadas = models.TextField(default='', help_text="Variables separadas por coma usadas en esta extracción")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"Extracción de {self.usuario.username} - {self.fecha_creacion.strftime('%Y-%m-%d')}"