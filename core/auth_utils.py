"""Utilitários de autenticação e escopo por hotel."""

from django.contrib.auth.models import User

from .models import Hotel, PapelUsuario, PAPEIS_ACESSO_GLOBAL, PerfilUsuario
from .hoteis import hoteis_rede_queryset


def get_perfil(user: User) -> PerfilUsuario | None:
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        return getattr(user, 'perfil', None)
    try:
        return user.perfil
    except PerfilUsuario.DoesNotExist:
        return None


def usuario_tem_papel(user: User, papeis: list[str]) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    perfil = get_perfil(user)
    if not perfil or not perfil.ativo:
        return False
    if perfil.papel == PapelUsuario.ADMIN:
        return True
    return perfil.papel in papeis


def usuario_acesso_global(user: User) -> bool:
    if user.is_superuser:
        return True
    perfil = get_perfil(user)
    return bool(perfil and perfil.ativo and perfil.acesso_global)


def get_hotel_escopo(user: User) -> Hotel | None:
    """Hotel fixo do perfil. None = vê todos os hotéis."""
    if usuario_acesso_global(user):
        return None
    perfil = get_perfil(user)
    if perfil and perfil.ativo and perfil.hotel_id:
        return perfil.hotel
    return None


def resolver_hotel_atual(request, hoteis_qs=None):
    """Hotel efetivo: perfil fixo > sessão > primeiro ativo."""
    from .models import Hotel

    hoteis_qs = hoteis_qs or hoteis_rede_queryset()
    hotel_fixo = get_hotel_escopo(request.user)
    if hotel_fixo:
        return hotel_fixo

    slug = request.session.get('hotel_slug')
    if slug:
        hotel = hoteis_qs.filter(slug=slug).first()
        if hotel:
            return hotel

    hotel = hoteis_qs.first()
    if hotel:
        request.session['hotel_slug'] = hotel.slug
    return hotel


def filtrar_queryset_por_hotel(queryset, user, campo_hotel='hotel'):
    hotel = get_hotel_escopo(user)
    if hotel:
        return queryset.filter(**{campo_hotel: hotel})
    return queryset
