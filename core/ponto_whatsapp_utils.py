"""Comprovante de batida de ponto via WhatsApp (link wa.me)."""

from __future__ import annotations

from django.utils import timezone

from .termo_utils import normalizar_telefone_whatsapp, url_whatsapp


def montar_mensagem_comprovante_ponto(batida, hotel) -> str:
    hora = timezone.localtime(batida.registrado_em).strftime('%d/%m/%Y às %H:%M')
    tipo = batida.get_tipo_display()
    extra = ' (extra/plantão)' if batida.extra_plantao else ''
    hotel_nome = hotel.nome if hotel else 'hotel'
    return (
        f'✅ *Comprovante de ponto — Vulcãozinho*\n\n'
        f'Hotel: {hotel_nome}\n'
        f'Recreador: {batida.recreador.nome}\n'
        f'Tipo: {tipo}{extra}\n'
        f'Data/hora: {hora}\n\n'
        'Guarde esta mensagem como comprovante da batida.'
    )


def contexto_whatsapp_comprovante(batida, hotel) -> dict:
    telefone = (batida.recreador.telefone or '').strip()
    mensagem = montar_mensagem_comprovante_ponto(batida, hotel)
    url = url_whatsapp(telefone, mensagem)
    return {
        'whatsapp_url': url,
        'whatsapp_disponivel': bool(normalizar_telefone_whatsapp(telefone)),
        'whatsapp_mensagem': mensagem,
    }
