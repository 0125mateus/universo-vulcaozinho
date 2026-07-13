"""App do hóspede (PWA) — MVP fase 1."""

import json

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View

from .auth_utils import resolver_hotel_atual
from .forms_hospede_app import HospedeAppLoginForm
from .hospede_app_auth import (
    buscar_hospede_login_global,
    buscar_hospedes_login_global,
    get_hospede_sessao,
    login_hospede,
    logout_hospede,
    primeiro_nome,
)
from .models import (
    InscricaoPasseio,
    NoiteTematica,
    Passeio,
    ProgramacaoDiaria,
    StatusPagamentoPasseio,
)
from .pix_utils import gerar_payload_pix


def _dia_semana_hoje():
    """weekday Python (seg=0) → DiaSemana do model (dom=0)."""
    return (timezone.localdate().weekday() + 1) % 7


def _passaporte_hospede(hospede):
    try:
        return hospede.passaporte
    except ObjectDoesNotExist:
        return None


class HospedeAppMixin:
    """Views autenticadas pela sessão do hóspede."""

    def dispatch(self, request, *args, **kwargs):
        self.hospede = get_hospede_sessao(request)
        if not self.hospede:
            return redirect(reverse('hospede_app_login') + '?next=' + request.path)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs) if hasattr(super(), 'get_context_data') else {}
        ctx['hospede'] = self.hospede
        ctx['hotel'] = self.hospede.hotel
        ctx['primeiro_nome'] = primeiro_nome(self.hospede.nome_completo)
        ctx['categoria'] = self.hospede.categoria_recreacao
        return ctx


class HospedeAppLoginView(View):
    template_name = 'hospede_app/login.html'

    def get(self, request):
        if get_hospede_sessao(request):
            return redirect('hospede_app_home')
        form = HospedeAppLoginForm(initial={'apartamento': request.GET.get('apt', '')})
        return render(request, self.template_name, {'form': form, 'hotel': None})

    def post(self, request):
        form = HospedeAppLoginForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form, 'hotel': None})

        apartamento = form.cleaned_data['apartamento']
        documento = form.cleaned_data['documento']
        matches = buscar_hospedes_login_global(apartamento, documento)

        if len(matches) > 1:
            messages.error(
                request,
                'Encontramos mais de um check-in com esses dados. Procure a recepção.',
            )
            return render(request, self.template_name, {'form': form, 'hotel': None})

        hospede = matches[0] if matches else None
        if not hospede:
            messages.error(
                request,
                'Não encontramos check-in ativo com esses dados. Confira apartamento e documento na recepção.',
            )
            return render(request, self.template_name, {'form': form, 'hotel': None})

        login_hospede(request, hospede)
        destino = request.GET.get('next') or reverse('hospede_app_home')
        return redirect(destino)


class HospedeAppIdentificarHotelView(View):
    """API leve: identifica o hotel pelo apartamento + documento (login do app)."""

    def get(self, request):
        apartamento = (request.GET.get('apartamento') or '').strip()
        documento = (request.GET.get('documento') or '').strip()
        from .documento_utils import normalizar_documento

        if not apartamento or len(normalizar_documento(documento)) < 4:
            return JsonResponse({'ok': False})

        matches = buscar_hospedes_login_global(apartamento, documento)
        if len(matches) != 1:
            return JsonResponse({'ok': False, 'ambiguo': len(matches) > 1})

        hospede = matches[0]
        hotel = hospede.hotel
        return JsonResponse({
            'ok': True,
            'hotel_nome': hotel.nome,
            'hotel_slug': hotel.slug,
            'hotel_cor': hotel.cor_primaria,
            'primeiro_nome': primeiro_nome(hospede.nome_completo),
        })


class HospedeAppLogoutView(View):
    def post(self, request):
        logout_hospede(request)
        return redirect('hospede_app_login')

    def get(self, request):
        logout_hospede(request)
        return redirect('hospede_app_login')


class HospedeAppHomeView(HospedeAppMixin, View):
    template_name = 'hospede_app/home.html'

    def get(self, request):
        hoje = timezone.localdate()
        cat = self.hospede.categoria_recreacao
        agora = timezone.localtime().time()

        qs = ProgramacaoDiaria.objects.filter(
            hotel=self.hospede.hotel, data=hoje,
        ).select_related('atividade', 'local', 'categoria').order_by('hora_inicio')

        if cat:
            qs_faixa = qs.filter(categoria=cat)
        else:
            qs_faixa = qs.none()

        acontecendo = qs_faixa.filter(hora_inicio__lte=agora, hora_fim__gt=agora).first()
        proxima = qs_faixa.filter(hora_inicio__gt=agora).first()
        a_seguir = list(qs_faixa.filter(hora_inicio__gt=agora)[:3])

        noite = NoiteTematica.objects.filter(
            hotel=self.hospede.hotel,
            dia_semana=_dia_semana_hoje(),
        ).first()

        passeios_hoje = Passeio.objects.filter(
            hotel=self.hospede.hotel, dia_semana=_dia_semana_hoje(), ativo=True,
        ).order_by('ordem', 'titulo')
        meus_passeios = set(
            InscricaoPasseio.objects.filter(hospede=self.hospede, data=hoje)
            .values_list('passeio_id', flat=True)
        )

        passaporte = _passaporte_hospede(self.hospede)

        return render(request, self.template_name, {
            'hospede': self.hospede,
            'hotel': self.hospede.hotel,
            'primeiro_nome': primeiro_nome(self.hospede.nome_completo),
            'categoria': cat,
            'acontecendo': acontecendo,
            'proxima_atividade': proxima,
            'a_seguir': a_seguir,
            'noite_hoje': noite,
            'passeios_hoje': passeios_hoje,
            'passeios_count': passeios_hoje.count(),
            'meus_passeios_count': len(meus_passeios),
            'passaporte': passaporte,
            'hoje': hoje,
        })


class HospedeAppProgramacaoView(HospedeAppMixin, View):
    template_name = 'hospede_app/programacao.html'

    def get(self, request):
        hoje = timezone.localdate()
        cat = self.hospede.categoria_recreacao

        programacoes = (
            ProgramacaoDiaria.objects.filter(hotel=self.hospede.hotel, data=hoje)
            .select_related('atividade', 'local', 'categoria', 'recreador')
            .order_by('hora_inicio')
        )

        if cat:
            minha_faixa = programacoes.filter(categoria=cat)
            outras = programacoes.exclude(categoria=cat)
        else:
            minha_faixa = programacoes
            outras = programacoes.none()

        return render(request, self.template_name, {
            'hospede': self.hospede,
            'hotel': self.hospede.hotel,
            'primeiro_nome': primeiro_nome(self.hospede.nome_completo),
            'categoria': cat,
            'minha_faixa': minha_faixa,
            'outras': outras,
            'hoje': hoje,
        })


class HospedeAppPasseiosView(HospedeAppMixin, View):
    template_name = 'hospede_app/passeios.html'

    def get(self, request):
        hoje = timezone.localdate()
        dia = _dia_semana_hoje()

        passeios_hoje = list(
            Passeio.objects.filter(
                hotel=self.hospede.hotel, dia_semana=dia, ativo=True,
            ).order_by('ordem', 'titulo')
        )
        semana = list(
            Passeio.objects.filter(hotel=self.hospede.hotel, ativo=True)
            .exclude(dia_semana=dia)
            .order_by('dia_semana', 'ordem')
        )

        inscricoes = {
            insc.passeio_id: insc
            for insc in InscricaoPasseio.objects.filter(
                hospede=self.hospede, data=hoje,
            )
        }
        for p in passeios_hoje:
            insc = inscricoes.get(p.id)
            p.inscrito = insc is not None
            p.inscricao = insc
            p.status_pag = insc.status_pagamento if insc else None
            p.precisa_pagar = bool(
                insc and insc.status_pagamento in (
                    StatusPagamentoPasseio.PENDENTE,
                    StatusPagamentoPasseio.REJEITADO,
                )
            )
            p.vagas_rest = p.vagas_restantes(hoje)
            p.esgotado = p.lotado(hoje) and not p.inscrito

        return render(request, self.template_name, {
            'hospede': self.hospede,
            'hotel': self.hospede.hotel,
            'primeiro_nome': primeiro_nome(self.hospede.nome_completo),
            'categoria': self.hospede.categoria_recreacao,
            'passeios_hoje': passeios_hoje,
            'semana': semana,
            'hoje': hoje,
        })


class HospedeAppPasseioInscricaoView(HospedeAppMixin, View):
    def post(self, request, pk):
        hoje = timezone.localdate()
        dia = _dia_semana_hoje()
        passeio = Passeio.objects.filter(
            pk=pk, hotel=self.hospede.hotel, dia_semana=dia, ativo=True,
        ).first()
        if not passeio:
            messages.error(request, 'Passeio indisponível para hoje.')
            return redirect('hospede_app_passeios')

        acao = request.POST.get('acao')
        inscricao = InscricaoPasseio.objects.filter(
            passeio=passeio, hospede=self.hospede, data=hoje,
        ).first()

        if acao == 'cancelar':
            if inscricao and inscricao.status_pagamento != StatusPagamentoPasseio.CONFIRMADO:
                inscricao.delete()
                messages.info(request, f'Inscrição no passeio "{passeio.titulo}" cancelada.')
            elif inscricao:
                messages.warning(request, 'Pagamento já confirmado. Procure a recepção para cancelar.')
        else:
            if inscricao:
                messages.info(request, 'Você já está inscrito neste passeio.')
            elif passeio.lotado(hoje):
                messages.error(request, 'Passeio lotado. Procure a recepção.')
            else:
                if passeio.is_gratuito:
                    status = StatusPagamentoPasseio.ISENTO
                    valor = None
                else:
                    status = StatusPagamentoPasseio.PENDENTE
                    valor = passeio.preco
                inscricao = InscricaoPasseio.objects.create(
                    passeio=passeio, hospede=self.hospede, data=hoje,
                    status_pagamento=status, valor=valor,
                )
                if not passeio.is_gratuito:
                    messages.success(request, 'Inscrição criada! Agora realize o pagamento via PIX.')
                    return redirect('hospede_app_passeio_pagamento', pk=passeio.pk)
                messages.success(request, f'Inscrição confirmada no passeio "{passeio.titulo}"!')

        return redirect('hospede_app_passeios')


class HospedeAppPasseioPagamentoView(HospedeAppMixin, View):
    template_name = 'hospede_app/passeio_pagamento.html'

    def _get_inscricao(self, pk):
        hoje = timezone.localdate()
        return InscricaoPasseio.objects.filter(
            passeio_id=pk, hospede=self.hospede, data=hoje,
        ).select_related('passeio', 'passeio__hotel').first()

    def get(self, request, pk):
        inscricao = self._get_inscricao(pk)
        if not inscricao:
            messages.error(request, 'Inscrição não encontrada.')
            return redirect('hospede_app_passeios')

        hotel = self.hospede.hotel
        passeio = inscricao.passeio
        if not inscricao.valor and passeio.preco and passeio.preco > 0:
            inscricao.valor = passeio.preco
            inscricao.save(update_fields=['valor'])

        chave_pix = passeio.pix_chave_efetiva
        valor_pix = inscricao.valor or passeio.preco
        if not valor_pix or valor_pix <= 0:
            valor_pix = None
        payload_pix = ''
        if chave_pix:
            payload_pix = gerar_payload_pix(
                chave_pix,
                passeio.pix_beneficiario_efetivo,
                hotel.cidade,
                valor=valor_pix,
                txid=f'PASSEIO{inscricao.pk}',
            )

        return render(request, self.template_name, {
            'hospede': self.hospede,
            'hotel': hotel,
            'primeiro_nome': primeiro_nome(self.hospede.nome_completo),
            'inscricao': inscricao,
            'passeio': passeio,
            'payload_pix': payload_pix,
            'chave_pix': chave_pix,
            'pix_indisponivel': not payload_pix,
        })

    def post(self, request, pk):
        inscricao = self._get_inscricao(pk)
        if not inscricao:
            messages.error(request, 'Inscrição não encontrada.')
            return redirect('hospede_app_passeios')

        arquivo = request.FILES.get('comprovante')
        if not arquivo:
            messages.error(request, 'Selecione o arquivo do comprovante.')
            return redirect('hospede_app_passeio_pagamento', pk=pk)

        if arquivo.size > 5 * 1024 * 1024:
            messages.error(request, 'Arquivo muito grande (máx. 5 MB).')
            return redirect('hospede_app_passeio_pagamento', pk=pk)

        inscricao.comprovante = arquivo
        inscricao.comprovante_enviado_em = timezone.now()
        inscricao.status_pagamento = StatusPagamentoPasseio.COMPROVANTE_ENVIADO
        inscricao.save(update_fields=[
            'comprovante', 'comprovante_enviado_em', 'status_pagamento',
        ])
        messages.success(request, 'Comprovante enviado! A recepção vai confirmar seu pagamento.')
        return redirect('hospede_app_passeio_pagamento', pk=pk)


class HospedeAppPassaporteView(HospedeAppMixin, View):
    template_name = 'hospede_app/passaporte.html'

    def get(self, request):
        passaporte = _passaporte_hospede(self.hospede)
        noites = NoiteTematica.objects.filter(hotel=self.hospede.hotel).order_by('dia_semana')
        carimbo_ids = set()
        if passaporte:
            carimbo_ids = set(passaporte.carimbos.values_list('noite_tematica_id', flat=True))

        return render(request, self.template_name, {
            'hospede': self.hospede,
            'hotel': self.hospede.hotel,
            'primeiro_nome': primeiro_nome(self.hospede.nome_completo),
            'categoria': self.hospede.categoria_recreacao,
            'passaporte': passaporte,
            'noites': noites,
            'carimbo_ids': carimbo_ids,
        })


class HospedeAppAssistantInitView(HospedeAppMixin, View):
    def get(self, request):
        from .hospede_app_assistant import saudacao, sugestoes

        return JsonResponse({
            'greeting': saudacao(self.hospede),
            'suggestions': sugestoes(),
            'ai_enabled': bool(settings.OPENAI_API_KEY),
        })


class HospedeAppAssistantChatView(HospedeAppMixin, View):
    def post(self, request):
        from .hospede_app_assistant import chat as assistant_chat

        try:
            payload = json.loads(request.body.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({'error': 'JSON inválido.'}, status=400)

        message = payload.get('message', '')
        history = payload.get('history', [])
        if not isinstance(history, list):
            history = []

        result = assistant_chat(message, history, self.hospede)
        if result.get('error') and not result.get('reply'):
            return JsonResponse(result, status=400)
        return JsonResponse(result)


class HospedeAppManifestView(View):
    """Manifest PWA para instalação na tela inicial."""

    def get(self, request):
        from django.conf import settings
        import json

        base = request.build_absolute_uri('/').rstrip('/')
        hotel = resolver_hotel_atual(request)
        icon_path = hotel.logo_static if hotel else 'img/mascote-vulcaozinho.png'
        app_name = hotel.nome if hotel else 'Vulcãozinho — App do Hóspede'
        manifest = {
            'name': f'{app_name} — App do Hóspede',
            'short_name': hotel.nome.split()[0] if hotel else 'Vulcãozinho',
            'description': 'Programação, passaporte e diversão no hotel',
            'start_url': f'{base}/app/',
            'scope': f'{base}/app/',
            'display': 'standalone',
            'background_color': '#fdfbf2',
            'theme_color': hotel.cor_primaria if hotel else '#1E6B43',
            'orientation': 'portrait',
            'lang': 'pt-BR',
            'icons': [
                {
                    'src': f'{base}/static/{icon_path}',
                    'sizes': '512x512',
                    'type': 'image/png',
                    'purpose': 'any maskable',
                },
            ],
        }
        return HttpResponse(
            json.dumps(manifest, ensure_ascii=False),
            content_type='application/manifest+json',
        )
