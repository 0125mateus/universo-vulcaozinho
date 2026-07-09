"""CRUD da programação diária (recepção / gestão)."""

from datetime import datetime

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .auth_utils import filtrar_queryset_por_hotel, resolver_hotel_atual
from .forms import ProgramacaoBulkCreateForm, ProgramacaoDiariaForm
from .mixins import PapelRequeridoMixin
from .models import ProgramacaoDiaria
from .views_programacao import PAPEIS_PUBLICAR_TELAO


class ProgramacaoGestaoMixin(PapelRequeridoMixin):
    papeis_requeridos = PAPEIS_PUBLICAR_TELAO
    titulo_acesso = 'Gestão de Programação'
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
        if getattr(self, 'form_class', None) is ProgramacaoDiariaForm:
            kwargs['hotel'] = self.hotel
        return kwargs

    def get_data_filtro(self):
        raw = self.request.GET.get('data') or self.request.POST.get('data')
        if raw:
            try:
                return datetime.strptime(raw, '%Y-%m-%d').date()
            except ValueError:
                pass
        return timezone.localdate()

    def get_success_url(self):
        data = self.object.data if hasattr(self, 'object') and self.object else self.get_data_filtro()
        return reverse('programacao_gestao') + f'?data={data.isoformat()}'


class ProgramacaoGestaoListView(ProgramacaoGestaoMixin, ListView):
    model = ProgramacaoDiaria
    template_name = 'programacao/gestao_list.html'
    context_object_name = 'programacoes'

    def get_queryset(self):
        data = self.get_data_filtro()
        return (
            self.escopo_queryset(ProgramacaoDiaria.objects.all())
            .filter(data=data)
            .select_related('atividade', 'local', 'categoria', 'recreador')
            .order_by('hora_inicio')
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['data_filtro'] = self.get_data_filtro()
        return ctx


class ProgramacaoCreateView(ProgramacaoGestaoMixin, CreateView):
    model = ProgramacaoDiaria
    form_class = ProgramacaoDiariaForm
    template_name = 'programacao/gestao_form.html'

    def get_initial(self):
        return {'data': self.get_data_filtro(), 'vagas_total': 30}

    def form_valid(self, form):
        messages.success(self.request, 'Atividade adicionada à programação.')
        return super().form_valid(form)


class ProgramacaoUpdateView(ProgramacaoGestaoMixin, UpdateView):
    model = ProgramacaoDiaria
    form_class = ProgramacaoDiariaForm
    template_name = 'programacao/gestao_form.html'

    def get_queryset(self):
        return self.escopo_queryset(ProgramacaoDiaria.objects.all())

    def form_valid(self, form):
        messages.success(self.request, 'Programação atualizada.')
        return super().form_valid(form)


class ProgramacaoDeleteView(ProgramacaoGestaoMixin, DeleteView):
    model = ProgramacaoDiaria
    template_name = 'programacao/gestao_confirm_delete.html'
    success_url = reverse_lazy('programacao_gestao')

    def get_queryset(self):
        return self.escopo_queryset(ProgramacaoDiaria.objects.all())

    def get_success_url(self):
        return reverse('programacao_gestao') + f'?data={self.object.data.isoformat()}'

    def form_valid(self, form):
        messages.info(self.request, 'Atividade removida da programação.')
        return super().form_valid(form)


class ProgramacaoBulkCreateView(ProgramacaoGestaoMixin, View):
    """Adiciona várias atividades de uma vez (horários em sequência)."""
    template_name = 'programacao/gestao_bulk_form.html'

    def get(self, request):
        initial = {'data': self.get_data_filtro(), 'hora_inicio': datetime.strptime('10:00', '%H:%M').time()}
        form = ProgramacaoBulkCreateForm(hotel=self.hotel, initial=initial)
        return self._render(form)

    def post(self, request):
        form = ProgramacaoBulkCreateForm(request.POST, hotel=self.hotel)
        if not form.is_valid():
            return self._render(form)

        criadas, erros = form.criar_programacoes()
        data = form.cleaned_data['data']
        if criadas:
            messages.success(
                request,
                f'{len(criadas)} atividade(s) adicionada(s) em {data.strftime("%d/%m/%Y")}.',
            )
        for err in erros:
            messages.warning(request, err)
        if not criadas and erros:
            return self._render(form)

        return redirect(reverse('programacao_gestao') + f'?data={data.isoformat()}')

    def _render(self, form):
        from django.shortcuts import render
        return render(self.request, self.template_name, {
            'form': form,
            'data_filtro': form.initial.get('data') or self.get_data_filtro(),
        })


class ProgramacaoBulkActionView(ProgramacaoGestaoMixin, View):
    """Ações em lote: excluir ou duplicar selecionadas."""

    def post(self, request):
        action = request.POST.get('action')
        ids = request.POST.getlist('ids')
        data_filtro = self.get_data_filtro()
        redirect_url = reverse('programacao_gestao') + f'?data={data_filtro.isoformat()}'

        if not ids:
            messages.warning(request, 'Nenhuma atividade selecionada.')
            return redirect(redirect_url)

        qs = self.escopo_queryset(ProgramacaoDiaria.objects.filter(pk__in=ids))

        if action == 'delete':
            n = qs.count()
            qs.delete()
            messages.info(request, f'{n} atividade(s) excluída(s).')
            return redirect(redirect_url)

        if action == 'duplicate':
            target_raw = request.POST.get('target_date', '').strip()
            try:
                target = datetime.strptime(target_raw, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, 'Informe uma data válida para duplicar.')
                return redirect(redirect_url)

            ok, falhas = 0, 0
            for prog in qs.order_by('hora_inicio'):
                try:
                    novo = ProgramacaoDiaria(
                        hotel=prog.hotel,
                        data=target,
                        hora_inicio=prog.hora_inicio,
                        hora_fim=prog.hora_fim,
                        atividade=prog.atividade,
                        local=prog.local,
                        categoria=prog.categoria,
                        recreador=prog.recreador,
                        vagas_total=prog.vagas_total,
                        observacoes=prog.observacoes,
                    )
                    novo.full_clean()
                    novo.save()
                    ok += 1
                except ValidationError:
                    falhas += 1

            if ok:
                messages.success(request, f'{ok} atividade(s) duplicada(s) para {target.strftime("%d/%m/%Y")}.')
            if falhas:
                messages.warning(request, f'{falhas} não puderam ser duplicadas (conflito de horário/local).')
            return redirect(reverse('programacao_gestao') + f'?data={target.isoformat()}')

        messages.error(request, 'Ação inválida.')
        return redirect(redirect_url)
