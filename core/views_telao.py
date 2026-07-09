from django.shortcuts import redirect, render
from django.views import View

from .auth_utils import resolver_hotel_atual
from .hoteis import hoteis_rede_queryset
from .models import Hotel


class TelaoView(View):
    """Tela fullscreen para TV — consome API pública do telão via JS."""

    def get(self, request, hotel_id=None):
        hotel = None
        if hotel_id:
            hotel = hoteis_rede_queryset().filter(pk=hotel_id).first()
        if not hotel:
            hotel = resolver_hotel_atual(request)
        if not hotel:
            return render(request, 'telao/sem_hotel.html')

        from django.conf import settings
        return render(request, 'telao/index.html', {
            'hotel': hotel,
            'telao_api_key': settings.TELAO_API_KEY,
            'telao_preview': request.GET.get('preview') == '1',
        })
