"""Cálculos e registro financeiro da loja."""

from __future__ import annotations

from decimal import Decimal

from django.db.models import Count, Sum
from django.utils import timezone

from .models import FormaPagamento, ProdutoLoja, VendaLoja
from .realtime import broadcast_hotel_update


def registrar_venda_loja(
    *,
    hotel,
    produto: ProdutoLoja,
    quantidade: int,
    forma_pagamento: str,
    registrado_por,
    descricao: str | None = None,
) -> VendaLoja:
    """Registra venda, calcula margem e baixa estoque."""
    if quantidade < 1:
        raise ValueError('Quantidade inválida.')
    if produto.estoque < quantidade:
        raise ValueError(f'Estoque insuficiente ({produto.estoque} un.).')

    preco = produto.preco or Decimal('0')
    custo = produto.custo or Decimal('0')
    valor_total = preco * quantidade
    custo_total = custo * quantidade

    venda = VendaLoja.objects.create(
        hotel=hotel,
        produto=produto,
        descricao=descricao or produto.nome,
        quantidade=quantidade,
        valor_unitario=preco,
        valor_total=valor_total,
        custo_unitario=custo,
        custo_total=custo_total,
        lucro_bruto=valor_total - custo_total,
        forma_pagamento=forma_pagamento,
        registrado_por=registrado_por,
    )
    produto.estoque -= quantidade
    produto.save(update_fields=['estoque'])
    broadcast_hotel_update(hotel.pk)
    return venda


def kpis_financeiros_loja(hotel, inicio_mes=None):
    """KPIs do mês corrente (ou a partir de inicio_mes)."""
    hoje = timezone.localdate()
    inicio = inicio_mes or hoje.replace(day=1)

    qs = VendaLoja.objects.filter(hotel=hotel, criado_em__date__gte=inicio)
    agg = qs.aggregate(
        receita=Sum('valor_total'),
        custo=Sum('custo_total'),
        lucro=Sum('lucro_bruto'),
    )
    receita = agg['receita'] or Decimal('0')
    custo = agg['custo'] or Decimal('0')
    lucro = agg['lucro'] or Decimal('0')
    qtd_vendas = qs.count()
    ticket_medio = round(receita / qtd_vendas, 2) if qtd_vendas else Decimal('0')
    margem_pct = round(float(lucro / receita * 100), 1) if receita else 0

    por_pagamento = []
    for fp, label in FormaPagamento.choices:
        total = qs.filter(forma_pagamento=fp).aggregate(t=Sum('valor_total'))['t'] or Decimal('0')
        if total:
            por_pagamento.append({
                'codigo': fp,
                'label': label,
                'total': total,
                'pct': round(float(total / receita * 100), 1) if receita else 0,
            })

    top_produtos = (
        qs.values('descricao')
        .annotate(total=Sum('valor_total'), qtd=Sum('quantidade'))
        .order_by('-total')[:5]
    )

    return {
        'inicio_mes': inicio,
        'receita_mes': receita,
        'custo_mes': custo,
        'lucro_mes': lucro,
        'margem_pct': margem_pct,
        'qtd_vendas_mes': qtd_vendas,
        'ticket_medio': ticket_medio,
        'por_pagamento': por_pagamento,
        'top_produtos': list(top_produtos),
    }
