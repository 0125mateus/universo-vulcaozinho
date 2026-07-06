from django.utils import timezone

from .auth_utils import get_perfil, resolver_hotel_atual
from .models import Hotel


def hotel_context(request):
    hoteis = Hotel.objects.filter(ativo=True)
    hotel = resolver_hotel_atual(request, hoteis)
    perfil = get_perfil(request.user) if request.user.is_authenticated else None

    pode_trocar_hotel = True
    if perfil and perfil.hotel_id:
        pode_trocar_hotel = False

    return {
        'hotel_atual': hotel,
        'hoteis_disponiveis': hoteis,
        'hoje': timezone.localdate(),
        'perfil_usuario': perfil,
        'pode_trocar_hotel': pode_trocar_hotel,
    }