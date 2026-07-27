# tu_app/templatetags/custom_tags.py
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

register = template.Library()

@register.filter
def get_item_var(texto_datos, key):
    """Busca 'key: valor' dentro de un string de texto separado por comas"""
    if not texto_datos:
        return "-"
    pares = texto_datos.split(', ')
    for par in pares:
        if ': ' in par:
            k, v = par.split(': ', 1)
            if k == key:
                return v
    return "-"