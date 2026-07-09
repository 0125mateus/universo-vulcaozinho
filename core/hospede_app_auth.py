"""Sessão do app do hóspede (PWA) — sem conta Django."""

from __future__ import annotations

from django.db.models import Q
from django.utils import timezone

from .documento_utils import normalizar_documento
from .models import Hospede

SESSION_KEY = 'hospede_app_id'


def buscar_hospede_login(hotel, apartamento: str, documento_entrada: str) -> Hospede | None:
    """Apartamento + documento (completo ou últimos 4 dígitos)."""
    apt = (apartamento or '').strip()
    chave = normalizar_documento(documento_entrada)
    if not apt or len(chave) < 4:
        return None

    hoje = timezone.localdate()
    candidatos = (
        Hospede.objects.filter(hotel=hotel, apartamento__iexact=apt)
        .filter(Q(data_checkout__isnull=True) | Q(data_checkout__gte=hoje))
        .select_related('hotel')
    )
    for hospede in candidatos:
        doc = normalizar_documento(hospede.documento)
        if doc == chave or doc.endswith(chave):
            return hospede
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
