from django.contrib import messages
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, ListView

from .auth_utils import filtrar_queryset_por_hotel, resolver_hotel_atual, usuario_tem_papel
from .forms import HospedeForm
from .mixins import PapelRequeridoMixin
from .models import (
    FaixaEtaria,
    Hospede,
    InscricaoAtividade,
    PapelUsuario,
    PresencaRegistro,
    ProgramacaoDiaria,
)

PAPEIS_RECEPCAO = [
    PapelUsuario.ADMIN,
    PapelUsuario.DIRETOR,
    PapelUsuario.GERENTE,
    PapelUsuario.SUPERVISOR,
    PapelUsuario.RECEPCAO,
]

PAPEIS_OVERRIDE_LOTADO = [
    PapelUsuario.ADMIN,
    PapelUsuario.DIRETOR,
    PapelUsuario.GERENTE,
]


class RecepcaoMixin(PapelRequeridoMixin):
    papeis_requeridos = PAPEIS_RECEPCAO
    titulo_acesso = 'Módulo Recepção'
    login_url = '/entrar/'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.hotel = resolver_hotel_atual(request)

    def hotel_required_response(self):
        messages.error(self.request, 'Selecione um hotel para usar a recepção.')
        return redirect('home')

    def escopo_queryset(self, queryset, campo_hotel='hotel'):
        qs = filtrar_queryset_por_hotel(queryset, self.request.user, campo_hotel)
        if self.hotel:
            qs = qs.filter(**{campo_hotel: self.hotel})
        return qs


def _hospedes_ativos_qs(hotel):
    hoje = timezone.localdate()
    return Hospede.objects.filter(hotel=hotel).filter(
        Q(data_checkout__isnull=True) | Q(data_checkout__gte=hoje)
    )


def _filtrar_por_faixa(qs, faixa):
    if not faixa:
        return qs
    ref = timezone.localdate()
    limites = {
        FaixaEtaria.BEBE: (0, 2),
        FaixaEtaria.INFANTIL: (3, 11),
        FaixaEtaria.ADOLESCENTE: (12, 17),
        FaixaEtaria.ADULTO: (18, 59),
        FaixaEtaria.IDOSO: (60, 120),
    }
    if faixa not in limites:
        return qs
    min_idade, max_idade = limites[faixa]

    def anos_atras(idade):
        try:
            return ref.replace(year=ref.year - idade)
        except ValueError:
            return ref.replace(year=ref.year - idade, day=28)

    return qs.filter(
        data_nascimento__lte=anos_atras(min_idade),
        data_nascimento__gte=anos_atras(max_idade),
    )


class RecepcaoIndexView(RecepcaoMixin, View):
    def get(self, request):
        if not self.hotel:
            return self.hotel_required_response()
        hoje = timezone.localdate()
        ativos = _hospedes_ativos_qs(self.hotel).count()
        programacoes = ProgramacaoDiaria.objects.filter(hotel=self.hotel, data=hoje).count()
        return render(request, 'recepcao/index.html', {
            'ativos': ativos,
            'programacoes_hoje': programacoes,
        })


class CheckinCreateView(RecepcaoMixin, CreateView):
    model = Hospede
    form_class = HospedeForm
    template_name = 'recepcao/checkin.html'
    success_url = reverse_lazy('recepcao_hospedes')

    def dispatch(self, request, *args, **kwargs):
        if not self.hotel:
            return self.hotel_required_response()
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['hotel'] = self.hotel
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['faixas'] = FaixaEtaria.choices
        return ctx

    def form_valid(self, form):
        form.instance.hotel = self.hotel
        messages.success(self.request, f'Check-in de {form.instance.nome_completo} realizado!')
        return super().form_valid(form)


class HospedeListView(RecepcaoMixin, ListView):
    model = Hospede
    template_name = 'recepcao/hospedes_list.html'
    context_object_name = 'hospedes'
    paginate_by = 25

    def dispatch(self, request, *args, **kwargs):
        if not self.hotel:
            return self.hotel_required_response()
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = self.escopo_queryset(_hospedes_ativos_qs(self.hotel))
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(Q(nome_completo__icontains=q) | Q(apartamento__icontains=q))
        faixa = self.request.GET.get('faixa', '').strip()
        qs = _filtrar_por_faixa(qs, faixa)
        return qs.order_by('nome_completo')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        ctx['faixa'] = self.request.GET.get('faixa', '')
        ctx['faixas'] = FaixaEtaria.choices
        return ctx


class HospedeCheckoutView(RecepcaoMixin, View):
    def post(self, request, pk):
        if not self.hotel:
            return self.hotel_required_response()
        hospede = get_object_or_404(
            self.escopo_queryset(Hospede.objects.all()),
            pk=pk,
        )
        if not hospede.ativo:
            messages.warning(request, 'Hóspede já está com check-out.')
        else:
            hospede.data_checkout = timezone.localdate()
            hospede.save(update_fields=['data_checkout', 'atualizado_em'])
            messages.success(request, f'Check-out de {hospede.nome_completo} registrado.')
        return redirect('recepcao_hospedes')


class AgendaDiaView(RecepcaoMixin, ListView):
    model = ProgramacaoDiaria
    template_name = 'recepcao/agenda.html'
    context_object_name = 'programacoes'

    def dispatch(self, request, *args, **kwargs):
        if not self.hotel:
            return self.hotel_required_response()
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        hoje = timezone.localdate()
        return (
            self.escopo_queryset(ProgramacaoDiaria.objects.all())
            .filter(data=hoje)
            .select_related('atividade', 'local', 'recreador', 'categoria')
            .annotate(inscritos=Count('inscricoes'), presentes_count=Count('presencas', filter=Q(presencas__presente=True)))
            .order_by('hora_inicio')
        )


class RegistrarPresencaView(RecepcaoMixin, View):
    template_name = 'recepcao/presenca.html'

    def _get_programacao(self, pk):
        return get_object_or_404(
            self.escopo_queryset(ProgramacaoDiaria.objects.all()),
            pk=pk,
        )

    def get(self, request, pk):
        if not self.hotel:
            return self.hotel_required_response()
        programacao = self._get_programacao(pk)
        hospedes = _hospedes_ativos_qs(self.hotel).order_by('nome_completo')
        ja_presentes = set(
            programacao.presencas.filter(presente=True).values_list('hospede_id', flat=True)
        )
        modal = request.GET.get('modal') == '1'
        ctx = {
            'programacao': programacao,
            'hospedes': hospedes,
            'ja_presentes': ja_presentes,
            'modal': modal,
        }
        if modal:
            return render(request, 'recepcao/presenca_modal.html', ctx)
        return render(request, self.template_name, ctx)

    def post(self, request, pk):
        if not self.hotel:
            return self.hotel_required_response()
        programacao = self._get_programacao(pk)
        presentes_ids = {int(x) for x in request.POST.getlist('presentes') if x.isdigit()}
        hospedes_validos = set(_hospedes_ativos_qs(self.hotel).values_list('pk', flat=True))
        presentes_ids &= hospedes_validos

        criados = 0
        for hid in presentes_ids:
            _, created = PresencaRegistro.objects.update_or_create(
                programacao=programacao,
                hospede_id=hid,
                defaults={'presente': True, 'registrado_por': request.user},
            )
            if created:
                criados += 1

        messages.success(
            request,
            f'Presença registrada para {len(presentes_ids)} hóspede(s) em {programacao.atividade.nome}.',
        )
        next_url = request.POST.get('next') or reverse('recepcao_agenda')
        return redirect(next_url)


class VincularAtividadeView(RecepcaoMixin, View):
    template_name = 'recepcao/vincular.html'

    def dispatch(self, request, *args, **kwargs):
        if not self.hotel:
            return self.hotel_required_response()
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        hoje = timezone.localdate()
        programacoes = (
            self.escopo_queryset(ProgramacaoDiaria.objects.all())
            .filter(data=hoje)
            .select_related('atividade', 'local')
            .annotate(inscritos=Count('inscricoes'))
            .order_by('hora_inicio')
        )
        prog_id = request.GET.get('programacao')
        programacao = programacoes.filter(pk=prog_id).first() if prog_id else programacoes.first()
        hospedes = _hospedes_ativos_qs(self.hotel).order_by('nome_completo')
        inscritos = set()
        if programacao:
            inscritos = set(programacao.inscricoes.values_list('hospede_id', flat=True))

        return render(request, self.template_name, {
            'programacoes': programacoes,
            'programacao': programacao,
            'hospedes': hospedes,
            'inscritos': inscritos,
            'pode_override': usuario_tem_papel(request.user, PAPEIS_OVERRIDE_LOTADO),
        })

    def post(self, request):
        hoje = timezone.localdate()
        prog_id = request.POST.get('programacao')
        programacao = get_object_or_404(
            self.escopo_queryset(ProgramacaoDiaria.objects.filter(data=hoje)),
            pk=prog_id,
        )
        selecionados = {int(x) for x in request.POST.getlist('hospedes') if x.isdigit()}
        hospedes_validos = set(_hospedes_ativos_qs(self.hotel).values_list('pk', flat=True))
        selecionados &= hospedes_validos
        override = request.POST.get('override_lotado') == '1'
        pode_override = usuario_tem_papel(request.user, PAPEIS_OVERRIDE_LOTADO)

        inscritos = 0
        avisos = []
        for hid in selecionados:
            if programacao.lotado() and not (override and pode_override):
                avisos.append('Atividade lotada — inscrições extras bloqueadas (apenas Gerente+ pode forçar).')
                break
            _, created = InscricaoAtividade.objects.get_or_create(
                programacao=programacao,
                hospede_id=hid,
            )
            if created:
                inscritos += 1
            if programacao.lotado() and not override:
                avisos.append(f'Limite de {programacao.vagas_total} vagas atingido.')
                break

        if inscritos:
            messages.success(request, f'{inscritos} inscrição(ões) confirmada(s).')
        for aviso in avisos:
            messages.warning(request, aviso)
        if not inscritos and not avisos:
            messages.info(request, 'Nenhuma nova inscrição (hóspedes já inscritos ou lista vazia).')

        return redirect(f'{reverse("recepcao_vincular")}?programacao={programacao.pk}')


class FaixaEtariaPreviewAPI(RecepcaoMixin, View):
    """Preview de faixa etária para o formulário de check-in (JS)."""

    http_method_names = ['get']

    def get(self, request):
        raw = request.GET.get('data_nascimento', '')
        try:
            from datetime import datetime
            nasc = datetime.strptime(raw, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return JsonResponse({'ok': False, 'erro': 'Data inválida.'}, status=400)

        from .models import calcular_faixa_etaria
        codigo = calcular_faixa_etaria(nasc)
        label = FaixaEtaria(codigo).label
        return JsonResponse({'ok': True, 'faixa': codigo, 'label': label})
