import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from django.views import View
from django.views.decorators.http import require_GET, require_POST

from .mixins import PapelRequeridoMixin
from .models import MensagemReuniao, PapelUsuario, SalaReuniao

PAPEIS_REUNIAO = [
    PapelUsuario.ADMIN,
    PapelUsuario.DIRETOR,
    PapelUsuario.GERENTE,
]


class ReuniaoView(PapelRequeridoMixin, View):
    papeis_requeridos = PAPEIS_REUNIAO
    titulo_acesso = 'Reunião — Diretoria e Gestão'

    def get(self, request):
        salas = SalaReuniao.objects.filter(ativa=True).select_related('hotel')
        sala_slug = request.GET.get('sala') or request.session.get('sala_reuniao')
        sala = salas.filter(slug=sala_slug).first() if sala_slug else salas.first()

        if sala:
            request.session['sala_reuniao'] = sala.slug

        mensagens = []
        if sala:
            mensagens = sala.mensagens.select_related('autor').order_by('-criado_em')[:50]
            mensagens = list(reversed(mensagens))

        return self._render(request, salas, sala, mensagens)

    def _render(self, request, salas, sala, mensagens):
        from django.shortcuts import render
        return render(request, 'core/reuniao.html', {
            'salas': salas,
            'sala_atual': sala,
            'mensagens_iniciais': mensagens,
            'usuario': request.user,
        })


class ReuniaoMensagensAPI(PapelRequeridoMixin, View):
    papeis_requeridos = PAPEIS_REUNIAO
    http_method_names = ['get']

    def get(self, request):
        sala = get_object_or_404(SalaReuniao, slug=request.GET.get('sala'), ativa=True)
        since_id = request.GET.get('since', 0)
        try:
            since_id = int(since_id)
        except (TypeError, ValueError):
            since_id = 0

        qs = sala.mensagens.select_related('autor').filter(id__gt=since_id).order_by('criado_em')[:100]
        data = [
            {
                'id': m.id,
                'autor': m.autor.get_full_name() or m.autor.username if m.autor else 'Sistema',
                'texto': m.texto,
                'hora': m.criado_em.strftime('%H:%M'),
                'eu': m.autor_id == request.user.id,
            }
            for m in qs
        ]
        return JsonResponse({'mensagens': data, 'sala': sala.slug})


class ReuniaoEnviarAPI(PapelRequeridoMixin, View):
    papeis_requeridos = PAPEIS_REUNIAO
    http_method_names = ['post']

    def post(self, request):
        try:
            payload = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON inválido.'}, status=400)

        sala = get_object_or_404(SalaReuniao, slug=payload.get('sala'), ativa=True)
        texto = (payload.get('texto') or '').strip()
        if not texto:
            return JsonResponse({'error': 'Mensagem vazia.'}, status=400)
        if len(texto) > 2000:
            return JsonResponse({'error': 'Mensagem muito longa.'}, status=400)

        msg = MensagemReuniao.objects.create(sala=sala, autor=request.user, texto=texto)
        return JsonResponse({
            'id': msg.id,
            'autor': request.user.get_full_name() or request.user.username,
            'texto': msg.texto,
            'hora': msg.criado_em.strftime('%H:%M'),
            'eu': True,
        })
