"""CRUD de passeios semanais (gestão)."""

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .auth_utils import filtrar_queryset_por_hotel, resolver_hotel_atual
from .forms import PasseioForm
from .mixins import PapelRequeridoMixin
from .models import DiaSemana, Passeio
from .pix_utils import gerar_payload_pix
from .views_programacao import PAPEIS_PUBLICAR_TELAO


class PasseiosGestaoMixin(PapelRequeridoMixin):
    papeis_requeridos = PAPEIS_PUBLICAR_TELAO
    titulo_acesso = 'Gestão de Passeios'
    login_url = '/entrar/'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.hotel = resolver_hotel_atual(request)

    def dispatch(self, request, *args, **kwargs):
        if not self.hotel:
            messages.error(request, 'Selecione um hotel.')
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)

    def escopo_queryset(self, queryset):
        qs = filtrar_queryset_por_hotel(queryset, self.request.user)
        return qs.filter(hotel=self.hotel)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['hotel'] = self.hotel
        return kwargs

    def get_success_url(self):
        return reverse('passeios_gestao')


class PasseiosGestaoListView(PasseiosGestaoMixin, ListView):
    model = Passeio
    template_name = 'passeios/gestao_list.html'
    context_object_name = 'passeios'

    def get_queryset(self):
        return self.escopo_queryset(Passeio.objects.all()).order_by('dia_semana', 'ordem')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        passeios = list(self.get_queryset())
        dias = []
        for valor, label in DiaSemana.choices:
            itens = [p for p in passeios if p.dia_semana == valor]
            dias.append({'valor': valor, 'label': label, 'passeios': itens})
        ctx['dias'] = dias
        return ctx


class PasseioCreateView(PasseiosGestaoMixin, CreateView):
    model = Passeio
    form_class = PasseioForm
    template_name = 'passeios/gestao_form.html'

    def get_initial(self):
        dia = self.request.GET.get('dia')
        initial = {'vagas': 0, 'ordem': 0}
        if dia is not None and dia.isdigit():
            initial['dia_semana'] = int(dia)
        return initial

    def form_valid(self, form):
        messages.success(self.request, 'Passeio adicionado.')
        return super().form_valid(form)


class PasseioUpdateView(PasseiosGestaoMixin, UpdateView):
    model = Passeio
    form_class = PasseioForm
    template_name = 'passeios/gestao_form.html'

    def get_queryset(self):
        return self.escopo_queryset(Passeio.objects.all())

    def form_valid(self, form):
        messages.success(self.request, 'Passeio atualizado.')
        return super().form_valid(form)


class PasseioDeleteView(PasseiosGestaoMixin, DeleteView):
    model = Passeio
    template_name = 'passeios/gestao_confirm_delete.html'
    success_url = reverse_lazy('passeios_gestao')

    def get_queryset(self):
        return self.escopo_queryset(Passeio.objects.all())

    def form_valid(self, form):
        messages.info(self.request, 'Passeio removido.')
        return super().form_valid(form)


class PasseioPixPreviewView(PasseiosGestaoMixin, View):
    """Gera o payload PIX (copia e cola) para pré-visualização na gestão."""

    http_method_names = ['get']

    def get(self, request):
        chave = (request.GET.get('chave') or '').strip()
        if not chave and self.hotel:
            chave = self.hotel.pix_chave
        nome = (request.GET.get('nome') or '').strip()
        if not nome and self.hotel:
            nome = self.hotel.pix_beneficiario or self.hotel.nome
        valor = request.GET.get('valor')
        cidade = self.hotel.cidade if self.hotel else 'POCOS DE CALDAS'

        if not chave:
            return JsonResponse({
                'ok': False,
                'erro': 'Defina a chave PIX do passeio ou do hotel (Admin → Hotéis).',
            })

        try:
            valor_num = float(str(valor).replace(',', '.')) if valor else None
        except ValueError:
            valor_num = None

        payload = gerar_payload_pix(chave, nome, cidade, valor=valor_num, txid='PASSEIO')
        return JsonResponse({
            'ok': True,
            'payload': payload,
            'chave': chave,
            'beneficiario': nome,
            'valor': valor_num,
        })
