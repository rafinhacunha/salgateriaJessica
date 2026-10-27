from django import template

from nucleo.utils import centavos_para_campo, formatar_brl

register = template.Library()
register.filter("brl", formatar_brl)
register.filter("campo_reais", centavos_para_campo)


@register.filter
def multiplicar(a, b):
    return int(a) * int(b)


@register.filter
def get_item(dicionario, chave):
    return dicionario.get(chave)
