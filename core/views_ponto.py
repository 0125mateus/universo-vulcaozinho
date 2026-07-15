"""Ponto eletrônico — quiosque tablet e gestão."""

from __future__ import annotations

from datetime import datetime, time as dtime, timedelta

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from .auth_utils import resolver_hotel_atual
from .mixins import PapelRequeridoMixin
from .models import PapelUsuario, PontoBatida, Recreador, TipoPontoBatida
from .ponto_service import (
    PontoErro,
    autenticar_por_nome_pin,
    estado_ponto_hoje,
    registrar_batida,
    validar_pin,
)


PAPEIS_PONTO_GESTAO = [
    PapelUsuario.ADMIN,
    PapelUsuario.DIRETOR,
    PapelUsuario.GERENTE,
    PapelUsuario.SUPERVISOR,
]

SESSION_RECREADOR_ID = 'ponto_recreador_id'


def _client_ip(request) -> str | None:
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _recreador_da_sessao(request) -> Recreador | None:
    rid = request.session.get(SESSION_RECREADOR_ID)
    if not rid:
        return None
    return Recreador.objects.filter(pk=rid, ativo=True).select_related('hotel').first()


def _estado_payload(recreador: Recreador) -> dict:
    estado = estado_ponto_hoje(recreador)
    return {
        'ok': True,
        'recreador_id': recreador.id,
        'nome': recreador.nome,
        'foto_url': recreador.foto.url if recreador.foto else '',
        'tem_pin': recreador.tem_pin,
        'proxima_acao': estado.proxima_acao,
        'proxima_acao_label': 'Entrada' if estado.proxima_acao == TipoPontoBatida.ENTRADA else 'Saída',
        'ultima_batida': (
            {
                'tipo': estado.ultima_batida.tipo,
                'hora': timezone.localtime(estado.ultima_batida.registrado_em).strftime('%H:%M'),
                'extra_plantao': estado.ultima_batida.extra_plantao,
            }
            if estado.ultima_batida
            else None
        ),
    }


class PontoQuiosqueView(View):
    """Grade pública de recreadores no tablet da sala."""

    template_name = 'ponto/quiosque.html'

    def get(self, request):
        hotel = resolver_hotel_atual(request)
        if not hotel:
            return render(request, 'ponto/sem_hotel.html')
        recreadores = Recreador.objects.filter(hotel=hotel, ativo=True).order_by('nome')
        return render(request, self.template_name, {
            'hotel': hotel,
            'recreadores': recreadores,
            'hoje': timezone.localdate(),
        })


class PontoRecreadorEstadoAPI(View):
    """Estado do ponto + validação leve de PIN (POST)."""

    def get(self, request, pk):
        hotel = resolver_hotel_atual(request)
        recreador = get_object_or_404(Recreador, pk=pk, ativo=True)
        if not hotel or recreador.hotel_id != hotel.id:
            return JsonResponse({'ok': False, 'erro': 'Recreador inválido para este hotel.'}, status=400)
        return JsonResponse(_estado_payload(recreador))

    def post(self, request, pk):
        """Valida PIN e devolve estado (sem gravar batida)."""
        hotel = resolver_hotel_atual(request)
        recreador = get_object_or_404(Recreador, pk=pk, ativo=True)
        if not hotel or recreador.hotel_id != hotel.id:
            return JsonResponse({'ok': False, 'erro': 'Recreador inválido para este hotel.'}, status=400)
        pin = request.POST.get('pin', '')
        try:
            validar_pin(recreador, pin)
        except PontoErro as e:
            return JsonResponse({'ok': False, 'erro': str(e)}, status=400)
        return JsonResponse(_estado_payload(recreador))


class PontoAutenticarAPI(View):
    """Identifica recreador por nome + PIN (quiosque / app)."""

    def post(self, request):
        hotel = resolver_hotel_atual(request)
        if not hotel:
            return JsonResponse({'ok': False, 'erro': 'Selecione o hotel primeiro.'}, status=400)
        nome = request.POST.get('nome', '')
        pin = request.POST.get('pin', '')
        try:
            recreador = autenticar_por_nome_pin(hotel, nome, pin)
        except PontoErro as e:
            return JsonResponse({'ok': False, 'erro': str(e)}, status=400)
        return JsonResponse(_estado_payload(recreador))


class PontoRegistrarAPI(View):
    def post(self, request, pk):
        hotel = resolver_hotel_atual(request)
        recreador = get_object_or_404(Recreador, pk=pk, ativo=True)
        if not hotel or recreador.hotel_id != hotel.id:
            return JsonResponse({'ok': False, 'erro': 'Recreador inválido para este hotel.'}, status=400)

        pin = request.POST.get('pin', '')
        tipo = request.POST.get('tipo') or None
        extra = request.POST.get('extra_plantao') in ('1', 'true', 'on', 'yes')
        foto = request.FILES.get('foto_auditoria')

        try:
            batida = registrar_batida(
                recreador=recreador,
                hotel=hotel,
                pin=pin,
                tipo=tipo,
                extra_plantao=extra,
                foto_auditoria=foto,
                ip=_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                registrado_por=request.user if request.user.is_authenticated else None,
            )
        except PontoErro as e:
            return JsonResponse({'ok': False, 'erro': str(e)}, status=400)

        return JsonResponse({
            'ok': True,
            'tipo': batida.tipo,
            'tipo_label': batida.get_tipo_display(),
            'extra_plantao': batida.extra_plantao,
            'hora': timezone.localtime(batida.registrado_em).strftime('%H:%M'),
            'mensagem': (
                f'{batida.get_tipo_display()} registrada às '
                f'{timezone.localtime(batida.registrado_em).strftime("%H:%M")}'
                + (' (extra/plantão)' if batida.extra_plantao else '')
            ),
        })


class PontoAppLoginView(View):
    """App do recreador — login com nome + PIN (estilo app do hóspede)."""

    template_name = 'ponto/app_login.html'

    def get(self, request):
        hotel = resolver_hotel_atual(request)
        if not hotel:
            return render(request, 'ponto/sem_hotel.html')
        if _recreador_da_sessao(request):
            return redirect('ponto_app_home')
        return render(request, self.template_name, {
            'hotel': hotel,
            'hoje': timezone.localdate(),
        })

    def post(self, request):
        hotel = resolver_hotel_atual(request)
        if not hotel:
            return render(request, 'ponto/sem_hotel.html')
        nome = request.POST.get('nome', '')
        pin = request.POST.get('pin', '')
        try:
            recreador = autenticar_por_nome_pin(hotel, nome, pin)
        except PontoErro as e:
            messages.error(request, str(e))
            return render(request, self.template_name, {
                'hotel': hotel,
                'hoje': timezone.localdate(),
                'nome': nome,
            })
        request.session[SESSION_RECREADOR_ID] = recreador.id
        return redirect('ponto_app_home')


class PontoAppLogoutView(View):
    def post(self, request):
        request.session.pop(SESSION_RECREADOR_ID, None)
        return redirect('ponto_app_login')

    def get(self, request):
        request.session.pop(SESSION_RECREADOR_ID, None)
        return redirect('ponto_app_login')


class PontoAppHomeView(View):
    """Painel pessoal para bater ponto após login."""

    template_name = 'ponto/app_home.html'

    def get(self, request):
        hotel = resolver_hotel_atual(request)
        recreador = _recreador_da_sessao(request)
        if not hotel:
            return render(request, 'ponto/sem_hotel.html')
        if not recreador or recreador.hotel_id != hotel.id:
            request.session.pop(SESSION_RECREADOR_ID, None)
            return redirect('ponto_app_login')
        return render(request, self.template_name, {
            'hotel': hotel,
            'recreador': recreador,
            'estado': estado_ponto_hoje(recreador),
            'hoje': timezone.localdate(),
        })

    def post(self, request):
        hotel = resolver_hotel_atual(request)
        recreador = _recreador_da_sessao(request)
        if not hotel or not recreador or recreador.hotel_id != hotel.id:
            request.session.pop(SESSION_RECREADOR_ID, None)
            return redirect('ponto_app_login')

        tipo = request.POST.get('tipo') or None
        extra = request.POST.get('extra_plantao') in ('1', 'true', 'on', 'yes')
        foto = request.FILES.get('foto_auditoria')
        try:
            batida = registrar_batida(
                recreador=recreador,
                hotel=hotel,
                tipo=tipo,
                extra_plantao=extra,
                foto_auditoria=foto,
                ip=_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                exigir_pin=False,
            )
            messages.success(
                request,
                f'{batida.get_tipo_display()} registrada às '
                f'{timezone.localtime(batida.registrado_em).strftime("%H:%M")}'
                + (' (extra/plantão)' if batida.extra_plantao else ''),
            )
        except PontoErro as e:
            messages.error(request, str(e))
        return redirect('ponto_app_home')


class PontoGestaoView(PapelRequeridoMixin, View):
    papeis_requeridos = PAPEIS_PONTO_GESTAO
    titulo_acesso = 'Gestão do Ponto'
    login_url = '/entrar/'
    template_name = 'ponto/gestao.html'

    def get(self, request):
        hotel = resolver_hotel_atual(request)
        if not hotel:
            return redirect('home')
        hoje = timezone.localdate()
        inicio = timezone.make_aware(datetime.combine(hoje, dtime.min))
        fim = inicio + timedelta(days=1)

        recreadores = Recreador.objects.filter(hotel=hotel).order_by('nome')
        batidas = (
            PontoBatida.objects.filter(hotel=hotel, registrado_em__gte=inicio, registrado_em__lt=fim)
            .select_related('recreador')
            .order_by('-registrado_em')
        )
        return render(request, self.template_name, {
            'hotel': hotel,
            'recreadores': recreadores,
            'batidas': batidas,
            'hoje': hoje,
        })


class PontoRecreadorConfigView(PapelRequeridoMixin, View):
    papeis_requeridos = PAPEIS_PONTO_GESTAO
    titulo_acesso = 'Configurar recreador'
    login_url = '/entrar/'
    template_name = 'ponto/recreador_config.html'

    def get(self, request, pk):
        hotel = resolver_hotel_atual(request)
        recreador = get_object_or_404(Recreador, pk=pk)
        if not hotel or recreador.hotel_id != hotel.id:
            messages.error(request, 'Recreador inválido para este hotel.')
            return redirect('ponto_gestao')
        return render(request, self.template_name, {'hotel': hotel, 'recreador': recreador})

    def post(self, request, pk):
        hotel = resolver_hotel_atual(request)
        recreador = get_object_or_404(Recreador, pk=pk)
        if not hotel or recreador.hotel_id != hotel.id:
            messages.error(request, 'Recreador inválido para este hotel.')
            return redirect('ponto_gestao')

        recreador.nome = request.POST.get('nome', recreador.nome).strip() or recreador.nome
        recreador.telefone = request.POST.get('telefone', '').strip()
        recreador.ativo = request.POST.get('ativo') in ('1', 'on', 'true')
        if request.FILES.get('foto'):
            recreador.foto = request.FILES['foto']
        pin = request.POST.get('pin', '').strip()
        pin2 = request.POST.get('pin_confirm', '').strip()
        if pin:
            if not pin.isdigit() or not (4 <= len(pin) <= 6):
                messages.error(request, 'PIN deve ter 4 a 6 dígitos numéricos.')
                return render(request, self.template_name, {'hotel': hotel, 'recreador': recreador})
            if pin != pin2:
                messages.error(request, 'Confirmação de PIN não confere.')
                return render(request, self.template_name, {'hotel': hotel, 'recreador': recreador})
            recreador.set_pin(pin)
        recreador.save()
        messages.success(request, f'Recreador {recreador.nome} atualizado.')
        return redirect('ponto_gestao')
