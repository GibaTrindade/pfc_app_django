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


@register.filter(name='dividir')
def dividir(value, arg=60):
    try:
        value = int(value)
    except:
        return ''
    if value >= 0:
        ch_percentual = round(value / arg * 100, 2) if value / arg * 100 <= 100 else 100

        return str(ch_percentual)+'%'
    else:
        return ''
