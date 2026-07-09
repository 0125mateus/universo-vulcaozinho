"""Views de programação e publicação no telão."""

from django.contrib import messages
from django.shortcuts import redirect
from django.utils import timezone
from django.views import View

from .auth_utils import resolver_hotel_atual
from .grade_utils import montar_grade_hotel
from .mixins import PapelRequeridoMixin
from .models import PapelUsuario, TelaoGradePublicada
from .realtime import broadcast_hotel_update

PAPEIS_PUBLICAR_TELAO = [
    PapelUsuario.ADMIN,
    PapelUsuario.DIRETOR,
    PapelUsuario.GERENTE,
    PapelUsuario.SUPERVISOR,
    PapelUsuario.RECEPCAO,
]


def grade_publicada_hoje(hotel, data=None):
    data = data or timezone.localdate()
    return TelaoGradePublicada.objects.filter(
        hotel=hotel, data=data, ativo=True,
    ).first()


def publicar_grade_no_telao(hotel, user, data=None) -> tuple[bool, str]:
    data = data or timezone.localdate()
    payload = montar_grade_hotel(hotel, data)
    if payload['total'] == 0:
        return False, 'Não há atividades na grade de hoje para publicar.'

    TelaoGradePublicada.objects.update_or_create(
        hotel=hotel,
        data=data,
        defaults={
            'total_atividades': payload['total'],
            'ativo': True,
            'publicado_por': user if user.is_authenticated else None,
        },
    )
    broadcast_hotel_update(hotel.pk, event='grade_publicada')
    return True, (
        f'Grade publicada no telão: {payload["total"]} atividades '
        f'em {len(payload["colunas"])} faixas.'
    )


class PublicarTelaoGradeView(PapelRequeridoMixin, View):
    """Publica a grade do dia no telão (POST)."""
    papeis_requeridos = PAPEIS_PUBLICAR_TELAO
    titulo_acesso = 'Publicar grade no telão'

    def post(self, request):
        hotel = resolver_hotel_atual(request)
        if not hotel:
            messages.error(request, 'Selecione um hotel.')
            return redirect('programacao')

        ok, msg = publicar_grade_no_telao(hotel, request.user)
        if ok:
            messages.success(request, msg)
        else:
            messages.warning(request, msg)
        return redirect('programacao')


class RemoverTelaoGradeView(PapelRequeridoMixin, View):
    """Remove a grade publicada do telão (POST)."""
    papeis_requeridos = PAPEIS_PUBLICAR_TELAO
    titulo_acesso = 'Publicar grade no telão'

    def post(self, request):
        hotel = resolver_hotel_atual(request)
        if not hotel:
            messages.error(request, 'Selecione um hotel.')
            return redirect('programacao')

        hoje = timezone.localdate()
        updated = TelaoGradePublicada.objects.filter(
            hotel=hotel, data=hoje, ativo=True,
        ).update(ativo=False)
        if updated:
            broadcast_hotel_update(hotel.pk, event='grade_removida')
            messages.info(request, 'Grade removida do telão.')
        else:
            messages.warning(request, 'Nenhuma grade estava publicada no telão.')
        return redirect('programacao')
