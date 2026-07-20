"""Monta contexto operacional ao vivo para o assistente inteligente."""

from django.db.models import Count, Q, Sum
from django.utils import timezone

from core.financeiro import kpis_financeiros_loja
from core.models import (
    Hospede,
    InscricaoPasseio,
    Passeio,
    PassaporteHospede,
    PontoBatida,
    ProdutoLoja,
    ProgramacaoDiaria,
    StatusPagamentoPasseio,
)


def montar_contexto_hotel(hotel) -> str:
    """Resumo textual do hotel hoje — alimenta IA e respostas guiadas."""
    if not hotel:
        return 'Nenhum hotel selecionado no momento.'

    hoje = timezone.localdate()
    dia_semana = (hoje.weekday() + 1) % 7
    linhas = [
        f'Hotel: {hotel.nome} ({hotel.cidade}/{hotel.estado}).',
        f'Data de hoje: {hoje.strftime("%d/%m/%Y")}.',
    ]

    hospedes = Hospede.objects.filter(hotel=hotel).filter(
        Q(data_checkout__isnull=True) | Q(data_checkout__gte=hoje),
    )
    total_hospedes = hospedes.count()
    linhas.append(f'Hóspedes ativos: {total_hospedes}.')

    por_faixa = (
        hospedes.filter(categoria_recreacao__isnull=False)
        .values('categoria_recreacao__nome')
        .annotate(q=Count('id'))
        .order_by('-q')
    )
    if por_faixa:
        linhas.append('Hóspedes por faixa:')
        for item in por_faixa[:6]:
            linhas.append(f"- {item['categoria_recreacao__nome']}: {item['q']}")

    progs = (
        ProgramacaoDiaria.objects.filter(hotel=hotel, data=hoje)
        .select_related('atividade', 'local', 'categoria')
        .annotate(presentes=Count('presencas', filter=Q(presencas__presente=True)))
        .order_by('hora_inicio')
    )
    if progs.exists():
        linhas.append('Programação de hoje:')
        for p in progs[:25]:
            vagas = p.vagas_total or 0
            occ = f'{p.presentes}/{vagas}' if vagas else f'{p.presentes} presentes'
            cat = p.categoria.nome if p.categoria_id else 'geral'
            linhas.append(
                f'- {p.hora_inicio:%H:%M}-{p.hora_fim:%H:%M} {p.atividade.nome} '
                f'({cat}, {p.local.nome}) · {occ}'
            )
    else:
        linhas.append('Nenhuma atividade programada para hoje.')

    passeios = Passeio.objects.filter(hotel=hotel, dia_semana=dia_semana, ativo=True)
    if passeios.exists():
        linhas.append('Passeios de hoje:')
        for pas in passeios:
            preco = 'incluso' if pas.is_gratuito else f'R$ {pas.preco}'
            linhas.append(f'- {pas.titulo} ({preco})')

    pendentes = InscricaoPasseio.objects.filter(
        passeio__hotel=hotel,
        data=hoje,
        status_pagamento=StatusPagamentoPasseio.PENDENTE,
    ).count()
    if pendentes:
        linhas.append(f'Inscrições em passeios aguardando pagamento hoje: {pendentes}.')

    passaportes = PassaporteHospede.objects.filter(hospede__hotel=hotel).annotate(
        carimbos_count=Count('carimbos'),
    )
    if passaportes.exists():
        com_carimbo = passaportes.filter(carimbos_count__gte=1).count()
        completos = passaportes.filter(carimbos_count__gte=7).count()
        linhas.append(f'Passaportes: {com_carimbo} com carimbo, {completos} completos (7+).')

    produtos_baixo = ProdutoLoja.objects.filter(
        Q(hotel=hotel) | Q(hotel__isnull=True),
        ativo=True,
        estoque__lte=5,
    ).count()
    if produtos_baixo:
        linhas.append(f'Produtos da loja com estoque baixo (≤5): {produtos_baixo}.')

    fin = kpis_financeiros_loja(hotel)
    if fin.get('receita_mes', 0) > 0:
        linhas.append(
            f'Loja no mês: receita R$ {fin["receita_mes"]:.2f}, '
            f'lucro R$ {fin.get("lucro_mes", 0):.2f}, '
            f'margem {fin.get("margem_pct", 0):.1f}%.'
        )

    batidas_hoje = PontoBatida.objects.filter(hotel=hotel, registrado_em__date=hoje).count()
    if batidas_hoje:
        linhas.append(f'Batidas de ponto registradas hoje: {batidas_hoje}.')

    return '\n'.join(linhas)
