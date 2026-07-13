from decimal import Decimal

from django.contrib import messages
from django.db.models import Sum
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .auth_utils import filtrar_queryset_por_hotel, resolver_hotel_atual
from .financeiro_operacional_import import (
    importar_atracoes_xlsx,
    importar_compras_xlsx,
    importar_eventos_recreacao_xlsx,
)
from .financeiro_operacional_export import (
    exportar_atracoes_xlsx,
    exportar_compras_xlsx,
    exportar_extras_recreadores_xlsx,
    nome_arquivo_atracoes,
    nome_arquivo_compras,
    nome_arquivo_extras,
)
from .financeiro_whatsapp_utils import (
    contexto_whatsapp_planilha,
    resolver_planilha_token,
    telefone_setor_pagamentos,
)
from .forms_financeiro_operacional import (
    ExtraRecreadorFormSet,
    ImportarXlsxForm,
    ItemCompraForm,
    PagamentoAtracaoForm,
    PeriodoOperacionalForm,
    WhatsAppSetorPagamentosForm,
)
from .mixins import PapelRequeridoMixin
from .models import (
    ExtraRecreador,
    ItemCompraSemanal,
    PagamentoAtracao,
    PapelUsuario,
    PeriodoOperacional,
    TipoPeriodoOperacional,
)

PAPEIS_FINANCEIRO = [
    PapelUsuario.ADMIN,
    PapelUsuario.DIRETOR,
    PapelUsuario.GERENTE,
    PapelUsuario.SUPERVISOR,
]

DIAS_SEMANA = (
    ('seg', 'Seg'),
    ('ter', 'Ter'),
    ('qua', 'Qua'),
    ('qui', 'Qui'),
    ('sex', 'Sex'),
    ('sab', 'Sáb'),
    ('dom', 'Dom'),
)


class FinanceiroOperacionalMixin(PapelRequeridoMixin):
    papeis_requeridos = PAPEIS_FINANCEIRO
    titulo_acesso = 'Financeiro operacional'
    login_url = '/entrar/'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.hotel = resolver_hotel_atual(request)

    def dispatch(self, request, *args, **kwargs):
        resp = super().dispatch(request, *args, **kwargs)
        if resp.status_code >= 400:
            return resp
        if not self.hotel and not request.user.is_superuser:
            messages.error(request, 'Selecione um hotel no topo da página.')
            return redirect('home')
        return resp

    def periodos_qs(self, tipo: str):
        qs = PeriodoOperacional.objects.filter(tipo=tipo)
        if self.hotel:
            qs = qs.filter(hotel=self.hotel)
        return filtrar_queryset_por_hotel(qs, self.request.user, 'hotel')

    def ctx_whatsapp_planilha(self, periodo, tipo: str) -> dict:
        return contexto_whatsapp_planilha(self.request, periodo, self.hotel, tipo)


class FinanceiroHubView(FinanceiroOperacionalMixin, View):
    template_name = 'financeiro/hub.html'

    def _hub_context(self, form_whatsapp=None):
        if form_whatsapp is None:
            form_whatsapp = WhatsAppSetorPagamentosForm(initial={
                'whatsapp_setor_pagamentos': self.hotel.whatsapp_setor_pagamentos,
            })
        telefone = telefone_setor_pagamentos(self.hotel)
        return {
            'periodos_extras': self.periodos_qs(TipoPeriodoOperacional.EXTRAS_RECREADORES)[:5],
            'periodos_atracoes': self.periodos_qs(TipoPeriodoOperacional.ATRACOES)[:5],
            'periodos_compras': self.periodos_qs(TipoPeriodoOperacional.COMPRAS)[:5],
            'total_atracoes': PagamentoAtracao.objects.filter(hotel=self.hotel).aggregate(
                t=Sum('valor'),
            )['t'] or Decimal('0'),
            'form_whatsapp': form_whatsapp,
            'whatsapp_setor_configurado': bool(telefone),
            'whatsapp_setor_numero': self.hotel.whatsapp_setor_pagamentos,
        }

    def get(self, request):
        return render(request, self.template_name, self._hub_context())

    def post(self, request):
        form_whatsapp = WhatsAppSetorPagamentosForm(request.POST)
        if form_whatsapp.is_valid():
            self.hotel.whatsapp_setor_pagamentos = form_whatsapp.cleaned_data['whatsapp_setor_pagamentos']
            self.hotel.save(update_fields=['whatsapp_setor_pagamentos', 'atualizado_em'])
            messages.success(request, 'WhatsApp do setor de pagamentos salvo.')
            return redirect('financeiro_hub')
        messages.error(request, 'Não foi possível salvar o número. Verifique o formato.')
        return render(request, self.template_name, self._hub_context(form_whatsapp=form_whatsapp))


class PeriodoCreateView(FinanceiroOperacionalMixin, CreateView):
    model = PeriodoOperacional
    form_class = PeriodoOperacionalForm
    template_name = 'financeiro/periodo_form.html'

    def get_tipo(self):
        return self.kwargs['tipo']

    def get_success_url(self):
        tipo = self.get_tipo()
        if tipo == TipoPeriodoOperacional.EXTRAS_RECREADORES:
            return reverse('financeiro_extras_periodo', kwargs={'pk': self.object.pk})
        if tipo == TipoPeriodoOperacional.COMPRAS:
            return reverse('financeiro_compras_periodo', kwargs={'pk': self.object.pk})
        return reverse('financeiro_atracoes_periodo', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['tipo'] = self.get_tipo()
        ctx['tipo_label'] = dict(TipoPeriodoOperacional.choices).get(self.get_tipo(), '')
        return ctx

    def form_valid(self, form):
        form.instance.hotel = self.hotel
        form.instance.tipo = self.get_tipo()
        form.instance.criado_por = self.request.user
        messages.success(self.request, f'Período "{form.instance.titulo}" criado.')
        return super().form_valid(form)


class ExtrasRecreadoresPeriodoView(FinanceiroOperacionalMixin, View):
    template_name = 'financeiro/extras_periodo.html'

    def get_periodo(self):
        return get_object_or_404(
            self.periodos_qs(TipoPeriodoOperacional.EXTRAS_RECREADORES),
            pk=self.kwargs['pk'],
        )

    def get(self, request, pk):
        periodo = self.get_periodo()
        formset = ExtraRecreadorFormSet(instance=periodo, queryset=periodo.extras_recreadores.all())
        return render(request, self.template_name, {
            'periodo': periodo,
            'formset': formset,
            'dias': DIAS_SEMANA,
            'totais_dia': self._totais_por_dia(periodo),
            'total_geral': sum(e.total for e in periodo.extras_recreadores.all()),
            **self.ctx_whatsapp_planilha(periodo, TipoPeriodoOperacional.EXTRAS_RECREADORES),
        })

    def post(self, request, pk):
        periodo = self.get_periodo()
        formset = ExtraRecreadorFormSet(
            request.POST,
            instance=periodo,
            queryset=periodo.extras_recreadores.all(),
        )
        if formset.is_valid():
            linhas = formset.save(commit=False)
            for i, extra in enumerate(linhas):
                extra.hotel = self.hotel
                extra.ordem = i
                extra.save()
            for obj in formset.deleted_objects:
                obj.delete()
            messages.success(request, 'Grade de extras salva.')
            return redirect('financeiro_extras_periodo', pk=pk)

        messages.error(request, 'Corrija os erros na grade.')
        extras = [f.instance for f in formset.forms if f not in formset.deleted_forms and f.cleaned_data.get('nome')]
        return render(request, self.template_name, {
            'periodo': periodo,
            'formset': formset,
            'dias': DIAS_SEMANA,
            'totais_dia': self._totais_de_formset(formset),
            'total_geral': self._total_geral_de_formset(formset),
            **self.ctx_whatsapp_planilha(periodo, TipoPeriodoOperacional.EXTRAS_RECREADORES),
        })

    def _totais_de_formset(self, formset):
        totais = {dia: Decimal('0') for dia, _ in DIAS_SEMANA}
        for form in formset.forms:
            if form in formset.deleted_forms:
                continue
            if not form.cleaned_data:
                continue
            if not form.cleaned_data.get('nome'):
                continue
            for dia, _ in DIAS_SEMANA:
                totais[dia] += form.cleaned_data.get(f'valor_{dia}') or Decimal('0')
        return totais

    def _total_geral_de_formset(self, formset):
        return sum(self._totais_de_formset(formset).values())

    def _totais_por_dia(self, periodo):
        extras = periodo.extras_recreadores.all()
        return {
            dia: sum(getattr(e, f'valor_{dia}') for e in extras)
            for dia, _ in DIAS_SEMANA
        }


class AtracoesPeriodoView(FinanceiroOperacionalMixin, View):
    template_name = 'financeiro/atracoes_periodo.html'

    def get_periodo(self):
        return get_object_or_404(
            self.periodos_qs(TipoPeriodoOperacional.ATRACOES),
            pk=self.kwargs['pk'],
        )

    def get(self, request, pk):
        periodo = self.get_periodo()
        pagamentos = periodo.pagamentos.all() if periodo else PagamentoAtracao.objects.none()
        if not pagamentos.exists():
            pagamentos = PagamentoAtracao.objects.filter(hotel=self.hotel, periodo=periodo)
        total = pagamentos.aggregate(t=Sum('valor'))['t'] or Decimal('0')
        return render(request, self.template_name, {
            'periodo': periodo,
            'pagamentos': pagamentos,
            'total': total,
            'import_form': ImportarXlsxForm(),
            **self.ctx_whatsapp_planilha(periodo, TipoPeriodoOperacional.ATRACOES),
        })

    def post(self, request, pk):
        periodo = self.get_periodo()
        form = ImportarXlsxForm(request.POST, request.FILES)
        if not form.is_valid():
            messages.error(request, 'Selecione um arquivo .xlsx válido.')
            return redirect('financeiro_atracoes_periodo', pk=pk)

        arquivo = form.cleaned_data['arquivo']
        substituir = form.cleaned_data['substituir']
        tipo_import = request.POST.get('tipo_import', 'atracoes')

        if tipo_import == 'eventos':
            criados, erros = importar_eventos_recreacao_xlsx(
                arquivo, self.hotel, periodo, substituir=substituir,
            )
        else:
            criados, erros = importar_atracoes_xlsx(
                arquivo, self.hotel, periodo, substituir=substituir,
            )

        if criados:
            messages.success(request, f'{criados} registro(s) importado(s).')
        for err in erros:
            messages.warning(request, err)
        return redirect('financeiro_atracoes_periodo', pk=pk)


class PagamentoAtracaoCreateView(FinanceiroOperacionalMixin, CreateView):
    model = PagamentoAtracao
    form_class = PagamentoAtracaoForm
    template_name = 'financeiro/atracao_form.html'

    def get_periodo(self):
        return get_object_or_404(
            self.periodos_qs(TipoPeriodoOperacional.ATRACOES),
            pk=self.kwargs['periodo_pk'],
        )

    def get_success_url(self):
        return reverse('financeiro_atracoes_periodo', kwargs={'pk': self.kwargs['periodo_pk']})

    def form_valid(self, form):
        form.instance.hotel = self.hotel
        form.instance.periodo = self.get_periodo()
        messages.success(self.request, 'Pagamento cadastrado.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['periodo'] = self.get_periodo()
        return ctx


class PagamentoAtracaoUpdateView(FinanceiroOperacionalMixin, UpdateView):
    model = PagamentoAtracao
    form_class = PagamentoAtracaoForm
    template_name = 'financeiro/atracao_form.html'
    pk_url_kwarg = 'pagamento_pk'

    def get_queryset(self):
        qs = PagamentoAtracao.objects.filter(hotel=self.hotel)
        return filtrar_queryset_por_hotel(qs, self.request.user, 'hotel')

    def get_success_url(self):
        return reverse('financeiro_atracoes_periodo', kwargs={'pk': self.object.periodo_id})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['periodo'] = self.object.periodo
        return ctx


class PagamentoAtracaoDeleteView(FinanceiroOperacionalMixin, DeleteView):
    model = PagamentoAtracao
    pk_url_kwarg = 'pagamento_pk'
    template_name = 'financeiro/confirmar_exclusao.html'

    def get_queryset(self):
        qs = PagamentoAtracao.objects.filter(hotel=self.hotel)
        return filtrar_queryset_por_hotel(qs, self.request.user, 'hotel')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['periodo'] = self.object.periodo
        ctx['titulo'] = f'Excluir pagamento — {self.object.artista}'
        ctx['voltar_url'] = reverse('financeiro_atracoes_periodo', kwargs={'pk': self.object.periodo_id})
        return ctx

    def get_success_url(self):
        return reverse('financeiro_atracoes_periodo', kwargs={'pk': self.object.periodo_id})


class ComprasListaView(FinanceiroOperacionalMixin, ListView):
    template_name = 'financeiro/compras_lista.html'
    context_object_name = 'periodos'

    def get_queryset(self):
        return self.periodos_qs(TipoPeriodoOperacional.COMPRAS)


class ComprasPeriodoView(FinanceiroOperacionalMixin, View):
    template_name = 'financeiro/compras_periodo.html'

    def get_periodo(self):
        return get_object_or_404(
            self.periodos_qs(TipoPeriodoOperacional.COMPRAS),
            pk=self.kwargs['pk'],
        )

    def get(self, request, pk):
        periodo = self.get_periodo()
        itens = ItemCompraSemanal.objects.filter(hotel=self.hotel, periodo=periodo)
        total = sum(i.preco_total for i in itens)
        return render(request, self.template_name, {
            'periodo': periodo,
            'itens': itens,
            'total': total,
            'import_form': ImportarXlsxForm(),
            'item_form': ItemCompraForm(),
            **self.ctx_whatsapp_planilha(periodo, TipoPeriodoOperacional.COMPRAS),
        })

    def post(self, request, pk):
        periodo = self.get_periodo()
        if 'importar' in request.POST:
            form = ImportarXlsxForm(request.POST, request.FILES)
            if form.is_valid():
                criados, erros = importar_compras_xlsx(
                    form.cleaned_data['arquivo'],
                    self.hotel,
                    periodo,
                    substituir=form.cleaned_data['substituir'],
                )
                if criados:
                    messages.success(request, f'{criados} item(ns) importado(s).')
                for err in erros:
                    messages.warning(request, err)
            else:
                messages.error(request, 'Arquivo inválido.')
            return redirect('financeiro_compras_periodo', pk=pk)

        form = ItemCompraForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.hotel = self.hotel
            item.periodo = periodo
            item.ordem = ItemCompraSemanal.objects.filter(periodo=periodo).count()
            item.save()
            messages.success(request, 'Item adicionado.')
        else:
            messages.error(request, 'Não foi possível adicionar o item.')
        return redirect('financeiro_compras_periodo', pk=pk)


class ItemCompraDeleteView(FinanceiroOperacionalMixin, DeleteView):
    model = ItemCompraSemanal
    template_name = 'financeiro/confirmar_exclusao.html'

    def get_queryset(self):
        qs = ItemCompraSemanal.objects.filter(hotel=self.hotel)
        return filtrar_queryset_por_hotel(qs, self.request.user, 'hotel')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['periodo'] = self.object.periodo
        ctx['titulo'] = f'Excluir item — {self.object.descricao[:40]}'
        ctx['voltar_url'] = reverse('financeiro_compras_periodo', kwargs={'pk': self.object.periodo_id})
        return ctx

    def get_success_url(self):
        return reverse('financeiro_compras_periodo', kwargs={'pk': self.object.periodo_id})


class ExtrasListaView(FinanceiroOperacionalMixin, ListView):
    template_name = 'financeiro/extras_lista.html'
    context_object_name = 'periodos'

    def get_queryset(self):
        return self.periodos_qs(TipoPeriodoOperacional.EXTRAS_RECREADORES)


class AtracoesListaView(FinanceiroOperacionalMixin, ListView):
    template_name = 'financeiro/atracoes_lista.html'
    context_object_name = 'periodos'

    def get_queryset(self):
        return self.periodos_qs(TipoPeriodoOperacional.ATRACOES)


def _xlsx_response(content: bytes, filename: str) -> HttpResponse:
    response = HttpResponse(
        content,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


class ExtrasRecreadoresExportView(FinanceiroOperacionalMixin, View):
    def get(self, request, pk):
        periodo = get_object_or_404(
            self.periodos_qs(TipoPeriodoOperacional.EXTRAS_RECREADORES),
            pk=pk,
        )
        content = exportar_extras_recreadores_xlsx(periodo)
        return _xlsx_response(content, nome_arquivo_extras(periodo))


class AtracoesExportView(FinanceiroOperacionalMixin, View):
    def get(self, request, pk):
        periodo = get_object_or_404(
            self.periodos_qs(TipoPeriodoOperacional.ATRACOES),
            pk=pk,
        )
        content = exportar_atracoes_xlsx(periodo)
        return _xlsx_response(content, nome_arquivo_atracoes(periodo))


class ComprasExportView(FinanceiroOperacionalMixin, View):
    def get(self, request, pk):
        periodo = get_object_or_404(
            self.periodos_qs(TipoPeriodoOperacional.COMPRAS),
            pk=pk,
        )
        content = exportar_compras_xlsx(periodo)
        return _xlsx_response(content, nome_arquivo_compras(periodo))


class FinanceiroPlanilhaPublicaView(View):
    """Download público da planilha via link assinado (compartilhamento WhatsApp)."""

    def get(self, request, token):
        resolved = resolver_planilha_token(token)
        if not resolved:
            raise Http404('Link da planilha inválido ou expirado.')

        periodo_pk, tipo = resolved
        periodo = PeriodoOperacional.objects.filter(pk=periodo_pk, tipo=tipo).first()
        if not periodo:
            raise Http404('Período não encontrado.')

        exportadores = {
            TipoPeriodoOperacional.EXTRAS_RECREADORES: (
                exportar_extras_recreadores_xlsx,
                nome_arquivo_extras,
            ),
            TipoPeriodoOperacional.ATRACOES: (
                exportar_atracoes_xlsx,
                nome_arquivo_atracoes,
            ),
            TipoPeriodoOperacional.COMPRAS: (
                exportar_compras_xlsx,
                nome_arquivo_compras,
            ),
        }
        exportador = exportadores.get(tipo)
        if not exportador:
            raise Http404('Tipo de planilha inválido.')

        export_fn, nome_fn = exportador
        content = export_fn(periodo)
        return _xlsx_response(content, nome_fn(periodo))
