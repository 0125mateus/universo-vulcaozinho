import json
import logging
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings

from .auth_utils import get_hotel_escopo, usuario_acesso_global
from .models import Hotel

logger = logging.getLogger(__name__)


class HotelLiveConsumer(AsyncWebsocketConsumer):
    """Base: entra no grupo do hotel e repassa eventos live."""

    async def connect(self):
        self.hotel_id = int(self.scope['url_route']['kwargs']['hotel_id'])
        if not await self._authorized():
            await self.close(code=4403)
            return

        self.group = f'hotel_{self.hotel_id}_live'
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()
        await self.send(text_data=json.dumps({
            'event': 'connected',
            'hotel_id': self.hotel_id,
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'group'):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def live_event(self, event):
        await self.send(text_data=json.dumps({
            'event': event.get('event', 'refresh'),
            'hotel_id': self.hotel_id,
        }))

    async def _authorized(self) -> bool:
        raise NotImplementedError


class DashboardConsumer(HotelLiveConsumer):
    """WebSocket autenticado — dashboard operacional."""

    async def _authorized(self) -> bool:
        user = self.scope.get('user')
        if user is None or not user.is_authenticated:
            return False
        exists = await database_sync_to_async(
            lambda: Hotel.objects.filter(pk=self.hotel_id, ativo=True).exists(),
        )()
        if not exists:
            return False
        if await database_sync_to_async(usuario_acesso_global)(user):
            return True
        escopo = await database_sync_to_async(get_hotel_escopo)(user)
        return escopo is not None and escopo.pk == self.hotel_id


class TelaoConsumer(HotelLiveConsumer):
    """WebSocket público — telão (API key na query string)."""

    async def _authorized(self) -> bool:
        expected = getattr(settings, 'TELAO_API_KEY', '')
        if not expected:
            return False
        query = parse_qs(self.scope.get('query_string', b'').decode())
        provided = (query.get('api_key') or [''])[0]
        if provided != expected:
            return False
        return await database_sync_to_async(
            lambda: Hotel.objects.filter(pk=self.hotel_id, ativo=True).exists(),
        )()
