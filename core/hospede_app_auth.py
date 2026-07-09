"""Sessão do app do hóspede (PWA) — sem conta Django."""

from __future__ import annotations

from django.db.models import Q
from django.utils import timezone

from .documento_utils import normalizar_documento
from .models import Hospede

SESSION_KEY = 'hospede_app_id'


def _hospedes_ativos_queryset(hotel=None):
    """Check-ins ativos, opcionalmente filtrados por hotel."""
    hoje = timezone.localdate()
    qs = Hospede.objects.filter(
        Q(data_checkout__isnull=True) | Q(data_checkout__gte=hoje),
    ).select_related('hotel')
    if hotel is not None:
        qs = qs.filter(hotel=hotel)
    else:
        from .hoteis import hoteis_rede_queryset

        qs = qs.filter(hotel__in=hoteis_rede_queryset())
    return qs


def _documento_confere(hospede: Hospede, chave: str) -> bool:
    doc = normalizar_documento(hospede.documento)
    return doc == chave or doc.endswith(chave)


def buscar_hospede_login(hotel, apartamento: str, documento_entrada: str) -> Hospede | None:
    """Apartamento + documento (completo ou últimos 4 dígitos) em um hotel."""
    apt = (apartamento or '').strip()
    chave = normalizar_documento(documento_entrada)
    if not apt or len(chave) < 4:
        return None

    for hospede in _hospedes_ativos_queryset(hotel).filter(apartamento__iexact=apt):
        if _documento_confere(hospede, chave):
            return hospede
    return None


def buscar_hospedes_login_global(apartamento: str, documento_entrada: str) -> list[Hospede]:
    """Busca check-in ativo em qualquer hotel da rede."""
    apt = (apartamento or '').strip()
    chave = normalizar_documento(documento_entrada)
    if not apt or len(chave) < 4:
        return []

    matches = []
    for hospede in _hospedes_ativos_queryset().filter(apartamento__iexact=apt):
        if _documento_confere(hospede, chave):
            matches.append(hospede)
    return matches


def buscar_hospede_login_global(apartamento: str, documento_entrada: str) -> Hospede | None:
    """Retorna hóspede único ou None (ambíguo / não encontrado)."""
    matches = buscar_hospedes_login_global(apartamento, documento_entrada)
    if len(matches) == 1:
        return matches[0]
    return None


def get_hospede_sessao(request) -> Hospede | None:
    pk = request.session.get(SESSION_KEY)
    if not pk:
        return None
    hoje = timezone.localdate()
    return (
        Hospede.objects.filter(pk=pk)
        .filter(Q(data_checkout__isnull=True) | Q(data_checkout__gte=hoje))
        .select_related('hotel')
        .prefetch_related('passaporte__carimbos__noite_tematica')
        .first()
    )


def login_hospede(request, hospede: Hospede) -> None:
    request.session[SESSION_KEY] = hospede.pk
    request.session['hotel_slug'] = hospede.hotel.slug


def logout_hospede(request) -> None:
    request.session.pop(SESSION_KEY, None)


def primeiro_nome(nome: str) -> str:
    return (nome or '').split()[0] if nome else 'Hóspede'
