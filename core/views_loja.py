from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from .auth_utils import filtrar_queryset_por_hotel, resolver_hotel_atual
from .financeiro import kpis_financeiros_loja, registrar_venda_loja
from .forms import ProdutoLojaForm
from .mixins import PapelRequeridoMixin
from .models import FormaPagamento, PapelUsuario, ProdutoLoja, VendaLoja

PAPEIS_LOJA = [
    PapelUsuario.ADMIN,
    PapelUsuario.DIRETOR,
    PapelUsuario.GERENTE,
    PapelUsuario.SUPERVISOR,
    PapelUsuario.LOJA,
]


class LojaGestaoMixin(PapelRequeridoMixin):
    papeis_requeridos = PAPEIS_LOJA
    titulo_acesso = 'Gestão da Loja'
    login_url = '/entrar/'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.hotel = resolver_hotel_atual(request)

    def produtos_qs(self):
        qs = ProdutoLoja.objects.filter(
            Q(hotel=self.hotel) | Q(hotel__isnull=True)
        )
        return filtrar_queryset_por_hotel(qs, self.request.user, 'hotel') if self.hotel else qs


class LojaGestaoView(LojaGestaoMixin, ListView):
    template_name = 'loja/gestao_list.html'
    context_object_name = 'produtos'
    paginate_by = 30

    def get_queryset(self):
        return self.produtos_qs().order_by('ordem', 'nome')

    def dispatch(self, request, *args, **kwargs):
        if not self.hotel and not self.request.user.is_superuser:
            messages.error(request, 'Selecione um hotel.')
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)


class ProdutoCreateView(LojaGestaoMixin, CreateView):
    model = ProdutoLoja
    form_class = ProdutoLojaForm
    template_name = 'loja/gestao_form.html'
    success_url = reverse_lazy('loja_gestao')

    def form_valid(self, form):
        if self.hotel:
            form.instance.hotel = self.hotel
        messages.success(self.request, f'Produto "{form.instance.nome}" cadastrado.')
        return super().form_valid(form)


class ProdutoUpdateView(LojaGestaoMixin, UpdateView):
    model = ProdutoLoja
    form_class = ProdutoLojaForm
    template_name = 'loja/gestao_form.html'
    success_url = reverse_lazy('loja_gestao')

    def get_queryset(self):
        return self.produtos_qs()

    def form_valid(self, form):
        messages.success(self.request, 'Produto atualizado.')
        return super().form_valid(form)


class ProdutoQRView(LojaGestaoMixin, View):
    def get(self, request, pk):
        produto = get_object_or_404(self.produtos_qs(), pk=pk)
        return render(request, 'loja/qr.html', {'produto': produto})


class ProdutoVendaView(LojaGestaoMixin, View):
    """Registra venda financeira e baixa estoque."""

    def post(self, request, pk):
        produto = get_object_or_404(self.produtos_qs(), pk=pk)
        qtd = max(1, int(request.POST.get('quantidade', 1)))
        forma = request.POST.get('forma_pagamento', FormaPagamento.PIX)
        try:
            venda = registrar_venda_loja(
                hotel=self.hotel or produto.hotel,
                produto=produto,
                quantidade=qtd,
                forma_pagamento=forma,
                registrado_por=request.user,
            )
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('loja_gestao')
        messages.success(
            request,
            f'Venda: {venda.quantidade}x {venda.descricao} — R$ {venda.valor_total} (margem {venda.margem_pct}%)',
        )
        return redirect('loja_gestao')


class LojaPDVView(LojaGestaoMixin, View):
    """PDV — ponto de venda com carrinho."""

    template_name = 'loja/pdv.html'

    def dispatch(self, request, *args, **kwargs):
        if not self.hotel and not request.user.is_superuser:
            messages.error(request, 'Selecione um hotel para o PDV.')
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        produtos = self.produtos_qs().filter(ativo=True, estoque__gt=0).order_by('ordem', 'nome')
        return render(request, self.template_name, {
            'produtos': produtos,
            'formas_pagamento': FormaPagamento.choices,
            'kpis': kpis_financeiros_loja(self.hotel) if self.hotel else {},
        })

    def post(self, request):
        forma = request.POST.get('forma_pagamento', FormaPagamento.PIX)
        ids = request.POST.getlist('produto_id')
        qtds = request.POST.getlist('quantidade')
        if not ids:
            messages.error(request, 'Carrinho vazio.')
            return redirect('loja_pdv')

        total_vendas = 0
        total_valor = 0
        erros = []
        for pid, qtd_str in zip(ids, qtds):
            try:
                qtd = max(1, int(qtd_str))
                produto = get_object_or_404(self.produtos_qs(), pk=int(pid))
                venda = registrar_venda_loja(
                    hotel=self.hotel,
                    produto=produto,
                    quantidade=qtd,
                    forma_pagamento=forma,
                    registrado_por=request.user,
                )
                total_vendas += 1
                total_valor += venda.valor_total
            except (ValueError, TypeError) as e:
                erros.append(str(e))

        if total_vendas:
            messages.success(
                request,
                f'PDV: {total_vendas} item(ns) — total R$ {total_valor:.2f}',
            )
        for err in erros:
            messages.warning(request, err)
        return redirect('loja_pdv')


class FinanceiroLojaView(LojaGestaoMixin, View):
    """Relatório financeiro mensal da loja."""

    template_name = 'loja/financeiro.html'

    def dispatch(self, request, *args, **kwargs):
        if not self.hotel:
            messages.error(request, 'Selecione um hotel.')
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        kpis = kpis_financeiros_loja(self.hotel)
        vendas = (
            VendaLoja.objects.filter(hotel=self.hotel, criado_em__date__gte=kpis['inicio_mes'])
            .select_related('produto', 'registrado_por')[:50]
        )
        return render(request, self.template_name, {
            'kpis': kpis,
            'vendas_recentes': vendas,
        })


class VendasLojaView(LojaGestaoMixin, ListView):
    template_name = 'loja/vendas_list.html'
    context_object_name = 'vendas'
    paginate_by = 40

    def get_queryset(self):
        if not self.hotel:
            return VendaLoja.objects.none()
        return VendaLoja.objects.filter(hotel=self.hotel).select_related('produto', 'registrado_por')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.hotel:
            ctx['kpis'] = kpis_financeiros_loja(self.hotel)
        return ctx
