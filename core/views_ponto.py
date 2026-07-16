"""Ponto eletrônico — quiosque tablet e gestão."""

from __future__ import annotations

import json
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
    FACE_VERIFY_TTL,
    PontoErro,
    autenticar_por_nome_pin,
    estado_ponto_hoje,
    registrar_batida,
    validar_pin,
    verificar_rosto,
)


PAPEIS_PONTO_GESTAO = [
    PapelUsuario.ADMIN,
    PapelUsuario.DIRETOR,
    PapelUsuario.GERENTE,
    PapelUsuario.SUPERVISOR,
]

SESSION_RECREADOR_ID = 'ponto_recreador_id'
SESSION_FACE_OK = 'ponto_face_ok'  # {recreador_id, expiso}


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


def _marcar_rosto_ok(request, recreador: Recreador) -> None:
    request.session[SESSION_FACE_OK] = {
        'recreador_id': recreador.id,
        'exp': (timezone.now() + FACE_VERIFY_TTL).isoformat(),
    }


def _rosto_ok(request, recreador: Recreador) -> bool:
    data = request.session.get(SESSION_FACE_OK) or {}
    if data.get('recreador_id') != recreador.id:
        return False
    exp = data.get('exp')
    if not exp:
        return False
    try:
        exp_dt = datetime.fromisoformat(exp)
        if timezone.is_naive(exp_dt):
            exp_dt = timezone.make_aware(exp_dt)
        return timezone.now() <= exp_dt
    except (TypeError, ValueError):
        return False


def _exigir_rosto_se_cadastrado(request, recreador: Recreador) -> None:
    if recreador.tem_reconhecimento_facial and not _rosto_ok(request, recreador):
        raise PontoErro('Confirme o reconhecimento facial antes de bater o ponto.')


def _estado_payload(recreador: Recreador) -> dict:
    estado = estado_ponto_hoje(recreador)
    return {
        'ok': True,
        'recreador_id': recreador.id,
        'nome': recreador.nome,
        'foto_url': recreador.foto.url if recreador.foto else '',
        'tem_pin': recreador.tem_pin,
        'tem_reconhecimento_facial': recreador.tem_reconhecimento_facial,
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
            _exigir_rosto_se_cadastrado(request, recreador)
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

        request.session.pop(SESSION_FACE_OK, None)
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


class PontoVerificarRostoAPI(View):
    """Compara descritor ao vivo com o cadastro."""

    def post(self, request, pk):
        hotel = resolver_hotel_atual(request)
        recreador = get_object_or_404(Recreador, pk=pk, ativo=True)
        if not hotel or recreador.hotel_id != hotel.id:
            return JsonResponse({'ok': False, 'erro': 'Recreador inválido para este hotel.'}, status=400)

        pin = request.POST.get('pin', '')
        if pin:
            try:
                validar_pin(recreador, pin)
            except PontoErro as e:
                return JsonResponse({'ok': False, 'erro': str(e)}, status=400)
        else:
            sess = _recreador_da_sessao(request)
            if not sess or sess.id != recreador.id:
                return JsonResponse({'ok': False, 'erro': 'Sessão inválida para reconhecimento.'}, status=400)

        descritor = request.POST.get('face_descriptor', '')
        try:
            dist = verificar_rosto(recreador, descritor)
        except PontoErro as e:
            return JsonResponse({'ok': False, 'erro': str(e)}, status=400)

        _marcar_rosto_ok(request, recreador)
        return JsonResponse({'ok': True, 'distancia': round(dist, 4), 'mensagem': 'Rosto confirmado.'})


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
            _exigir_rosto_se_cadastrado(request, recreador)
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
            request.session.pop(SESSION_FACE_OK, None)
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
        data_str = (request.GET.get('data') or '').strip()
        if data_str:
            try:
                dia = datetime.strptime(data_str, '%Y-%m-%d').date()
            except ValueError:
                dia = hoje
        else:
            dia = hoje

        inicio = timezone.make_aware(datetime.combine(dia, dtime.min))
        fim = inicio + timedelta(days=1)
        recreador_id = request.GET.get('recreador') or ''

        recreadores = Recreador.objects.filter(hotel=hotel).order_by('nome')
        batidas_qs = (
            PontoBatida.objects.filter(hotel=hotel, registrado_em__gte=inicio, registrado_em__lt=fim)
            .select_related('recreador', 'registrado_por')
            .order_by('-registrado_em')
        )
        if recreador_id.isdigit():
            batidas_qs = batidas_qs.filter(recreador_id=int(recreador_id))

        batidas = list(batidas_qs)
        resumo = {
            'total': len(batidas),
            'entradas': sum(1 for b in batidas if b.tipo == TipoPontoBatida.ENTRADA),
            'saidas': sum(1 for b in batidas if b.tipo == TipoPontoBatida.SAIDA),
            'extras': sum(1 for b in batidas if b.extra_plantao),
            'com_foto': sum(1 for b in batidas if b.foto_auditoria),
        }

        por_recreador = []
        for r in recreadores:
            do_dia = [b for b in batidas if b.recreador_id == r.id]
            if not do_dia and recreador_id:
                continue
            if not do_dia:
                continue
            por_recreador.append({
                'recreador': r,
                'batidas': sorted(do_dia, key=lambda b: b.registrado_em),
                'entradas': sum(1 for b in do_dia if b.tipo == TipoPontoBatida.ENTRADA),
                'saidas': sum(1 for b in do_dia if b.tipo == TipoPontoBatida.SAIDA),
                'extras': sum(1 for b in do_dia if b.extra_plantao),
            })

        return render(request, self.template_name, {
            'hotel': hotel,
            'recreadores': recreadores,
            'batidas': batidas,
            'hoje': hoje,
            'dia': dia,
            'recreador_filtro': recreador_id,
            'resumo': resumo,
            'por_recreador': por_recreador,
        })


def _aplicar_form_recreador(request, recreador, *, pin_obrigatorio: bool = False):
    """Aplica POST no recreador. Retorna mensagem de erro ou None."""
    nome = request.POST.get('nome', '').strip()
    if not nome:
        return 'Informe o nome do recreador.'
    recreador.nome = nome
    recreador.telefone = request.POST.get('telefone', '').strip()
    recreador.ativo = request.POST.get('ativo') in ('1', 'on', 'true')
    if request.FILES.get('foto'):
        recreador.foto = request.FILES['foto']
    face_raw = request.POST.get('face_descriptor', '').strip()
    if face_raw:
        try:
            recreador.set_face_descriptor(face_raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            return 'Descritor facial inválido. Tire a foto novamente.'
    elif request.FILES.get('foto'):
        recreador.face_descriptor = None

    pin = request.POST.get('pin', '').strip()
    pin2 = request.POST.get('pin_confirm', '').strip()
    if pin_obrigatorio and not pin and not recreador.tem_pin:
        return 'Defina um PIN de 4 a 6 dígitos.'
    if pin:
        if not pin.isdigit() or not (4 <= len(pin) <= 6):
            return 'PIN deve ter 4 a 6 dígitos numéricos.'
        if pin != pin2:
            return 'Confirmação de PIN não confere.'
        recreador.set_pin(pin)
    return None


def _mensagem_apos_salvar(recreador, *, criado: bool = False) -> tuple[str, str]:
    """Retorna (level, message)."""
    verbo = 'cadastrado' if criado else 'atualizado'
    if recreador.foto and not recreador.tem_reconhecimento_facial:
        return (
            'warning',
            f'{recreador.nome} {verbo}, mas o reconhecimento facial não foi gerado. '
            'Abra Configurar e tire a foto na câmera até “Rosto detectado”.',
        )
    if recreador.tem_reconhecimento_facial:
        return 'success', f'{recreador.nome} {verbo} com reconhecimento facial.'
    return 'success', f'Recreador {recreador.nome} {verbo}.'


class PontoRecreadorNovoView(PapelRequeridoMixin, View):
    papeis_requeridos = PAPEIS_PONTO_GESTAO
    titulo_acesso = 'Novo recreador'
    login_url = '/entrar/'
    template_name = 'ponto/recreador_novo.html'

    def get(self, request):
        hotel = resolver_hotel_atual(request)
        if not hotel:
            return redirect('home')
        return render(request, self.template_name, {'hotel': hotel})

    def post(self, request):
        hotel = resolver_hotel_atual(request)
        if not hotel:
            return redirect('home')
        recreador = Recreador(hotel=hotel, ativo=True)
        erro = _aplicar_form_recreador(request, recreador, pin_obrigatorio=True)
        if erro:
            messages.error(request, erro)
            return render(request, self.template_name, {
                'hotel': hotel,
                'nome': request.POST.get('nome', ''),
                'telefone': request.POST.get('telefone', ''),
            })
        recreador.save()
        level, msg = _mensagem_apos_salvar(recreador, criado=True)
        getattr(messages, level)(request, msg)
        return redirect('ponto_recreador_config', pk=recreador.pk)


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

        erro = _aplicar_form_recreador(request, recreador, pin_obrigatorio=False)
        if erro:
            messages.error(request, erro)
            return render(request, self.template_name, {'hotel': hotel, 'recreador': recreador})
        recreador.save()
        level, msg = _mensagem_apos_salvar(recreador, criado=False)
        getattr(messages, level)(request, msg)
        return redirect('ponto_gestao')


class PontoRecreadorExcluirView(PapelRequeridoMixin, View):
    papeis_requeridos = PAPEIS_PONTO_GESTAO
    titulo_acesso = 'Excluir recreador'
    login_url = '/entrar/'

    def post(self, request, pk):
        hotel = resolver_hotel_atual(request)
        recreador = get_object_or_404(Recreador, pk=pk)
        if not hotel or recreador.hotel_id != hotel.id:
            messages.error(request, 'Recreador inválido para este hotel.')
            return redirect('ponto_gestao')

        nome = recreador.nome
        if request.session.get(SESSION_RECREADOR_ID) == recreador.id:
            request.session.pop(SESSION_RECREADOR_ID, None)
        request.session.pop(SESSION_FACE_OK, None)
        recreador.delete()
        messages.success(request, f'Recreador {nome} excluído.')
        return redirect('ponto_gestao')
