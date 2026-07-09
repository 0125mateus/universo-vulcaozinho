"""Compartilhamento do termo de responsabilidade (link público + WhatsApp)."""

from __future__ import annotations

import re
from urllib.parse import quote

from django.core import signing
from django.urls import reverse

TERMO_SHARE_SALT = 'hospede-termo-share'
TERMO_SHARE_MAX_AGE = 60 * 60 * 24 * 90  # 90 dias


def assinar_token_termo(hospede_pk: int) -> str:
    return signing.dumps({'pk': hospede_pk}, salt=TERMO_SHARE_SALT)


def resolver_hospede_pk_token_termo(token: str) -> int | None:
    try:
        data = signing.loads(token, salt=TERMO_SHARE_SALT, max_age=TERMO_SHARE_MAX_AGE)
        return int(data['pk'])
    except (signing.BadSignature, signing.SignatureExpired, KeyError, ValueError, TypeError):
        return None


def normalizar_telefone_whatsapp(telefone: str) -> str:
    """E.164 Brasil (55 + DDD + número)."""
    digits = re.sub(r'\D', '', telefone or '')
    if not digits:
        return ''
    if digits.startswith('0'):
        digits = digits.lstrip('0')
    if not digits.startswith('55'):
        digits = '55' + digits
    return digits


def montar_mensagem_termo_whatsapp(hospede, hotel, url_termo: str) -> str:
    responsavel = (hospede.responsavel_nome or 'responsável').strip()
    hotel_nome = hotel.nome if hotel else 'hotel'
    return (
        f'Olá, {responsavel}! Segue o termo de responsabilidade para as atividades de '
        f'recreação do(a) {hospede.nome_completo} no {hotel_nome}:\n\n'
        f'{url_termo}\n\n'
        'Acesse o link para visualizar, imprimir ou salvar em PDF.'
    )


def url_whatsapp(telefone: str, mensagem: str) -> str:
    numero = normalizar_telefone_whatsapp(telefone)
    if not numero:
        return ''
    return f'https://wa.me/{numero}?text={quote(mensagem)}'


def contexto_compartilhamento_termo(request, hospede, hotel) -> dict:
    token = assinar_token_termo(hospede.pk)
    path = reverse('termo_publico', kwargs={'token': token})
    url_publica = request.build_absolute_uri(path)
    mensagem = montar_mensagem_termo_whatsapp(hospede, hotel, url_publica)
    telefone = hospede.responsavel_telefone or ''
    return {
        'termo_url_publica': url_publica,
        'whatsapp_termo_url': url_whatsapp(telefone, mensagem),
        'whatsapp_termo_disponivel': bool(normalizar_telefone_whatsapp(telefone)),
    }
