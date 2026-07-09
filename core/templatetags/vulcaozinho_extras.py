from django import template

from core.documento_utils import formatar_documento

register = template.Library()


@register.filter(name='doc_formatado')
def doc_formatado(valor):
    return formatar_documento(valor or '')
