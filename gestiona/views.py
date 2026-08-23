import pandas as pd
from django.http import HttpResponse, JsonResponse, response
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from datetime import timedelta
from servicios.models import Servicio, Plan, Suscripcion
import json # Lo usaremos solo para serializar a texto en el frontend, no en la BD
from .models import Extraccion, VariableUsuario
from saas_cobosis.settings import GROK_API
import requests
import json
import os
from openai import OpenAI
from django.conf import settings

# Inicializar cliente OpenAI
""" client = OpenAI(
    api_key=GROK_API,
    base_url="https://api.x.ai/v1"
) """

import requests
import json

class GroqClient:
    def __init__(self):
        self.api_key = GROK_API
        self.url = "https://api.groq.com/openai/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        print(self.headers)
        # No definimos system_prompt aquí, lo construimos dinámicamente

    def generate(self, texto: str, variables_str: str) -> str:
        try:
            system_prompt = (
                "Eres un asistente experto en procesamiento de datos y extracción de información. "
                f"Tu tarea es analizar el texto del usuario y extraer los valores para las siguientes variables: {variables_str}. "
                "Reglas estrictas:\n"
                "1. Debes responder ÚNICAMENTE con un objeto JSON válido. No incluyas texto adicional."
                "2. Las claves del JSON deben ser exactamente los nombres de las variables solicitadas."
                "3. Si una variable no se encuentra en el texto, su valor debe ser null."
                "4. Si de una variable se encuentra más de un valor, reflejalos como valores diferentes de la misma entrada, pero sin valores repetidos."
                "5. Si hay variables relacionadas, asegúrate de extraerlas correctamente y reflejarlas en el JSON."
            )
            data = {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": texto}
                ],
                "model": "llama-3.1-8b-instant",   # Modelo gratuito
                "max_tokens": 150,
                "temperature": 0.2,
                "response_format": { "type": "json_object" }   # CORREGIDO
            }

            response = requests.post(self.url, headers=self.headers, json=data)
            response.raise_for_status()   # Lanza excepción si hay error HTTP

            contenido_json = response.json()
            # Acceso correcto a los datos
            contenido = contenido_json['choices'][0]['message']['content']
            return contenido

        except requests.exceptions.RequestException as e:
            return f"Error de red/HTTP: {str(e)}"
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            return f"Error al procesar la respuesta: {str(e)}"
        except Exception as e:
            return f"Error inesperado: {str(e)}"

def procesar_texto_con_ia(texto, variables_solicitadas):
    """
    Llama a la API de Groq para extraer variables específicas.
    Retorna un diccionario con los valores extraídos.
    """
    if not variables_solicitadas:
        return {}

    variables_str = ", ".join(variables_solicitadas)
    client = GroqClient()

    try:
        resultado_str = client.generate(texto, variables_str)
        if resultado_str.startswith("Error"):
            print(f"Error en la generación: {resultado_str}")
            return {var: "Error IA" for var in variables_solicitadas}

        # Intentar parsear el JSON
        datos = json.loads(resultado_str)
        print(f"Datos extraidos: {datos}")  # Para depuración
        # Asegurar que todas las variables solicitadas estén presentes
        for var in variables_solicitadas:
            if var not in datos:
                datos[var] = None
            if var == 'cantidad':
                datos[var] = 1
        return datos

    except json.JSONDecodeError as e:
        print(f"Error al decodificar JSON: {e}. Respuesta: {resultado_str}")
        return {var: "Error IA" for var in variables_solicitadas}
    except Exception as e:
        print(f"Error inesperado: {e}")
        return {var: "Error IA" for var in variables_solicitadas}

@login_required
def gestiona_panel(request):
    # Obtenemos LA suscripción activa actual
    suscripcion = Suscripcion.objects.filter(
        usuario=request.user, 
        plan__servicio__slug='gestiona', 
        estado='activa'
    ).select_related('plan').first()

    if not suscripcion:
        return render(request, 'gestiona/no_suscripcion.html', {'servicio': 'Gestiona'})

    plan = suscripcion.plan
    
    variables_usuario = VariableUsuario.objects.filter(usuario=request.user).order_by('orden')
    variables_lista = [v.nombre for v in variables_usuario]

    # Lógica de guardado de variables
    if request.method == 'POST' and 'guardar_config' in request.POST:
        # Regla 1: Si es plan fijo y YA tiene variables, no permitir cambio.
        if not plan.variables_ajustables and variables_lista:
            messages.error(request, 'Tu plan actual no permite modificar las variables una vez configuradas.')
            return redirect('gestiona_panel')
        
        # Regla 2: Planes ajustables o fijos sin configurar todavía
        variables_input = request.POST.get('variables_input', '')
        nuevas_vars = [v.strip() for v in variables_input.split(',') if v.strip()]
        
        if len(nuevas_vars) > plan.max_variables:
            messages.error(request, f'Excediste el límite de {plan.max_variables} variables.')
        elif len(nuevas_vars) == 0:
            messages.error(request, 'Debes definir al menos una variable.')
        else:
            # Guardar las nuevas variables
            variables_usuario.delete()
            for i, var_name in enumerate(nuevas_vars):
                VariableUsuario.objects.create(usuario=request.user, nombre=var_name, orden=i)
            messages.success(request, 'Variables guardadas correctamente.')
            return redirect('gestiona_panel')

    # Historial de extracciones de la suscripción actual
    extracciones = Extraccion.objects.filter(suscripcion=suscripcion)
    extracciones_realizadas = extracciones.count()
    limite_alcanzado = plan.max_extracciones > 0 and extracciones_realizadas >= plan.max_extracciones

    # Variables para la tabla dinámica
    todas_las_variables = set(variables_lista)
    for ext in extracciones:
        if ext.variables_utilizadas:
            todas_las_variables.update(ext.variables_utilizadas.split(', '))
    todas_las_variables = sorted(list(todas_las_variables))

    context = {
        'plan': plan,
        'variables_fijas': variables_lista,
        'extracciones': extracciones,
        'limite_alcanzado': limite_alcanzado,
        'extracciones_realizadas': extracciones_realizadas,
        'todas_las_variables': todas_las_variables,
    }
    return render(request, 'gestiona/gestiona_panel.html', context)


@login_required
def gestiona_procesar(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    suscripcion = Suscripcion.objects.filter(
        usuario=request.user, 
        plan__servicio__slug='gestiona', 
        estado='activa'
    ).select_related('plan').first()
    
    if not suscripcion:
        return JsonResponse({'error': 'No tienes suscripción activa'}, status=403)

    plan = suscripcion.plan
    texto = request.POST.get('texto', '').strip()
    
    if not texto:
        return JsonResponse({'error': 'El texto no puede estar vacío'}, status=400)

    # Validar límites
    extracciones_actuales = Extraccion.objects.filter(suscripcion=suscripcion)
    if plan.max_extracciones > 0 and extracciones_actuales.count() >= plan.max_extracciones:
        return JsonResponse({'error': f'Has alcanzado el límite de {plan.max_extracciones} extracciones de tu plan actual.'}, status=403)

    # LÓGICA UNIFICADA: Ambos planes usan las variables guardadas en BD
    vars_obj = VariableUsuario.objects.filter(usuario=request.user).order_by('orden')
    variables_solicitadas = [v.nombre for v in vars_obj]
        
    if not variables_solicitadas:
        return JsonResponse({'error': 'Debes configurar tus variables primero en el panel superior.'}, status=400)

    # Llamar a la IA
    datos_dict = procesar_texto_con_ia(texto, variables_solicitadas)

    datos_texto = ", ".join([f"{k}: {v}" for k, v in datos_dict.items()])
    variables_usadas_texto = ", ".join(variables_solicitadas)

    # Guardar en BD
    nueva_extraccion = Extraccion.objects.create(
        usuario=request.user,
        suscripcion=suscripcion,
        texto_original=texto,
        datos_extraidos=datos_texto,
        variables_utilizadas=variables_usadas_texto
    )

    return JsonResponse({
        'success': True,
        'id': nueva_extraccion.id,
        'fecha': nueva_extraccion.fecha_creacion.strftime('%Y-%m-%d %H:%M'),
        'datos': datos_dict,
        'variables_usadas': variables_solicitadas
    })


@login_required
def gestiona_exportar_excel(request):
    suscripcion = Suscripcion.objects.filter(
        usuario=request.user, 
        plan__servicio__slug='gestiona', 
        estado='activa'
    ).select_related('plan').first()
    
    if not suscripcion:
        return HttpResponse('No autorizado', status=403)

    plan = suscripcion.plan
    
    # Filtrar solo por la suscripción activa
    extracciones = Extraccion.objects.filter(suscripcion=suscripcion)

    data = []
    todas_vars = set()
    for ext in extracciones:
        if ext.variables_utilizadas:
            todas_vars.update(ext.variables_utilizadas.split(', '))
    columnas = sorted(list(todas_vars))

    for ext in extracciones:
        fecha_formateada = ext.fecha_creacion.strftime('%Y-%m-%d %H:%M')
        fila = {'texto_original': ext.texto_original, 'fecha': fecha_formateada}
        
        pares = ext.datos_extraidos.split(', ')
        for par in pares:
            if ': ' in par:
                k, v = par.split(': ', 1)
                fila[k] = v
        for col in columnas:
            if col not in fila:
                fila[col] = "-"
        data.append(fila)

    df = pd.DataFrame(data)
    if columnas:
        cols = columnas + ['texto_original', 'fecha']
        df = df[cols]
        
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="gestion_cobosis.xlsx"'
    df.to_excel(response, index=False)
    
    return response


def detalle_gestiona(request):
    # Busca el servicio con slug 'gestiona'
    servicio = get_object_or_404(Servicio, slug='gestiona', activo=True)
    # Obtiene los planes activos ordenados por precio (o por el campo 'orden')
    planes = servicio.planes.filter(activo=True).order_by('precio')
    
    context = {
        'servicio': servicio,
        'planes': planes
    }
    return render(request, 'gestiona/detalle_gestiona.html', context)