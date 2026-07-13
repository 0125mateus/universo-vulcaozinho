"""Compartilhamento de planilhas do financeiro operacional via WhatsApp."""

from __future__ import annotations

from django.conf import settings
from django.core import signing
from django.urls import reverse

from .models import TipoPeriodoOperacional
from .termo_utils import normalizar_telefone_whatsapp, url_whatsapp

PLANILHA_SHARE_SALT = 'financeiro-planilha-share'
PLANILHA_SHARE_MAX_AGE = 60 * 60 * 24 * 7  # 7 dias

TIPO_LABELS = {
    TipoPeriodoOperacional.EXTRAS_RECREADORES: 'extras de recreadores',
    TipoPeriodoOperacional.ATRACOES: 'pagamentos de atrações / artistas',
    TipoPeriodoOperacional.COMPRAS: 'compras semanais de materiais',
}


def assinar_token_planilha(periodo_pk: int, tipo: str) -> str:
    return signing.dumps({'pk': periodo_pk, 'tipo': tipo}, salt=PLANILHA_SHARE_SALT)


def resolver_planilha_token(token: str) -> tuple[int, str] | None:
    try:
        data = signing.loads(token, salt=PLANILHA_SHARE_SALT, max_age=PLANILHA_SHARE_MAX_AGE)
        return int(data['pk']), str(data['tipo'])
    except (signing.BadSignature, signing.SignatureExpired, KeyError, ValueError, TypeError):
        return None


def telefone_setor_pagamentos(hotel) -> str:
    if hotel and getattr(hotel, 'whatsapp_setor_pagamentos', ''):
        return hotel.whatsapp_setor_pagamentos.strip()
    return getattr(settings, 'WHATSAPP_SETOR_PAGAMENTOS', '').strip()


def montar_mensagem_planilha_whatsapp(periodo, hotel, url_planilha: str, tipo: str) -> str:
    label = TIPO_LABELS.get(tipo, 'planilha financeira')
    hotel_nome = hotel.nome if hotel else 'hotel'
    return (
        f'Olá! Segue a planilha de {label} do {hotel_nome}.\n\n'
        f'Período: {periodo.titulo} '
        f'({periodo.data_inicio.strftime("%d/%m/%Y")} a {periodo.data_fim.strftime("%d/%m/%Y")})\n\n'
        f'Baixe o arquivo Excel pelo link:\n{url_planilha}\n\n'
        'Enviado pelo sistema Vulcãozinho.'
    )


def contexto_whatsapp_planilha(request, periodo, hotel, tipo: str) -> dict:
    token = assinar_token_planilha(periodo.pk, tipo)
    path = reverse('financeiro_planilha_publica', kwargs={'token': token})
    url_publica = request.build_absolute_uri(path)
    telefone = telefone_setor_pagamentos(hotel)
    mensagem = montar_mensagem_planilha_whatsapp(periodo, hotel, url_publica, tipo)
    return {
        'planilha_url_publica': url_publica,
        'whatsapp_planilha_url': url_whatsapp(telefone, mensagem),
        'whatsapp_planilha_disponivel': bool(normalizar_telefone_whatsapp(telefone)),
    }
