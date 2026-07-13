from django import template

from core.documento_utils import formatar_documento
from core.hotel_brand import FALLBACK_LOGO, hotel_logo_static_path

register = template.Library()


@register.filter(name='doc_formatado')
def doc_formatado(valor):
    return formatar_documento(valor or '')


@register.filter(name='hotel_logo')
def hotel_logo(hotel):
    if hotel is None:
        return FALLBACK_LOGO
    return hotel.logo_static


@register.simple_tag
def hotel_logo_path(slug):
    return hotel_logo_static_path(slug)
