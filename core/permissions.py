from rest_framework import permissions

from .auth_utils import get_hotel_escopo, get_perfil
from .models import Hotel


class HotelScopedPermission(permissions.BasePermission):
    """
    Exige usuário autenticado com perfil ativo (ou superuser).
    Em nível de objeto, restringe ao hotel do PerfilUsuario.
    """

    message = 'Sem permissão para acessar recursos deste hotel.'

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        perfil = get_perfil(user)
        return perfil is not None and perfil.ativo

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        hotel_obj = _hotel_do_objeto(obj)
        if hotel_obj is None:
            return True
        hotel_usuario = get_hotel_escopo(request.user)
        if hotel_usuario is None:
            return True
        return hotel_obj.pk == hotel_usuario.pk


def _hotel_do_objeto(obj) -> Hotel | None:
    if isinstance(obj, Hotel):
        return obj
    if hasattr(obj, 'hotel_id'):
        return obj.hotel
    if hasattr(obj, 'programacao_id'):
        return obj.programacao.hotel
    return None
