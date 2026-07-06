"""Broadcast em tempo real via Django Channels."""

from __future__ import annotations

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)

GROUP_PREFIX = 'hotel_'


def hotel_group_name(hotel_id: int) -> str:
    return f'{GROUP_PREFIX}{hotel_id}_live'


def broadcast_hotel_update(hotel_id: int | None, event: str = 'refresh') -> None:
    """Notifica dashboard e telão do hotel para recarregar dados."""
    if not hotel_id:
        return
    layer = get_channel_layer()
    if layer is None:
        return
    try:
        async_to_sync(layer.group_send)(
            hotel_group_name(hotel_id),
            {'type': 'live.event', 'event': event},
        )
    except Exception:
        logger.exception('Falha ao broadcast hotel %s', hotel_id)


def broadcast_all_hotels(event: str = 'refresh') -> None:
    from .models import Hotel

    for hid in Hotel.objects.filter(ativo=True).values_list('id', flat=True):
        broadcast_hotel_update(hid, event)
