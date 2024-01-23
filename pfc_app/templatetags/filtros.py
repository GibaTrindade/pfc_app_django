from django import template

register = template.Library()

@register.filter(name='custom_pluralize')
def custom_pluralize(value, arg='s'):
    try:
        value = int(value)
    except:
        return ''
    if value > 1:
        return arg
    else:
        return ''
