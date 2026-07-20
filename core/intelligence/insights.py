"""Motor de insights — analisa dados e sugere ações."""

from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone

from core.analise_faixas import cruzar_banco
from core.models import (
    Hospede,
    InscricaoPasseio,
    Passeio,
    ProdutoLoja,
    ProgramacaoDiaria,
    StatusPagamentoPasseio,
)


def _insight(tipo, titulo, descricao, *, prioridade='media', acao=None, acao_url=None):
    return {
        'tipo': tipo,
        'titulo': titulo,
        'descricao': descricao,
        'prioridade': prioridade,
        'acao': acao,
        'acao_url': acao_url,
    }


def gerar_insights(hotel) -> list[dict]:
    """Analisa o hotel e retorna recomendações acionáveis."""
    if not hotel:
        return [_insight(
            'info', 'Selecione um hotel',
            'Use o seletor no topo para ver insights personalizados.',
            prioridade='baixa',
        )]

    hoje = timezone.localdate()
    dia_semana = (hoje.weekday() + 1) % 7
    insights: list[dict] = []

    hospedes_ativos = Hospede.objects.filter(hotel=hotel).filter(
        Q(data_checkout__isnull=True) | Q(data_checkout__gte=hoje),
    ).count()

    progs = ProgramacaoDiaria.objects.filter(hotel=hotel, data=hoje).annotate(
        presentes=Count('presencas', filter=Q(presencas__presente=True)),
    )
    n_prog = progs.count()

    if n_prog == 0:
        insights.append(_insight(
            'alerta', 'Sem programação hoje',
            'Não há atividades cadastradas para hoje. Publique a grade ou rode o seed de programação.',
            prioridade='alta',
            acao='Ver programação',
            acao_url=reverse('programacao'),
        ))
    elif hospedes_ativos > 0:
        baixa_ocupacao = [
            p for p in progs
            if p.vagas_total and p.presentes < max(1, int(p.vagas_total * 0.25))
        ]
        if len(baixa_ocupacao) >= 2:
            insights.append(_insight(
                'ocupacao', 'Ocupação baixa em atividades',
                f'{len(baixa_ocupacao)} atividade(s) com menos de 25% de presença. '
                'Considere divulgar no telão ou ajustar horários.',
                prioridade='media',
                acao='Dashboard',
                acao_url=reverse('dashboard'),
            ))

    if hospedes_ativos == 0:
        insights.append(_insight(
            'info', 'Nenhum hóspede ativo',
            'Faça check-in na recepção para alimentar faixas, passaporte e presença.',
            prioridade='media',
            acao='Recepção',
            acao_url=reverse('recepcao_index'),
        ))

    pendentes = InscricaoPasseio.objects.filter(
        passeio__hotel=hotel,
        data=hoje,
        status_pagamento=StatusPagamentoPasseio.PENDENTE,
    ).count()
    if pendentes:
        insights.append(_insight(
            'financeiro', 'Pagamentos de passeio pendentes',
            f'{pendentes} inscrição(ões) aguardando pagamento hoje.',
            prioridade='alta',
            acao='Conferir pagamentos',
            acao_url=reverse('recepcao_passeios_pagamentos'),
        ))

    estoque_baixo = ProdutoLoja.objects.filter(
        Q(hotel=hotel) | Q(hotel__isnull=True),
        ativo=True,
        estoque__lte=5,
    ).count()
    if estoque_baixo:
        insights.append(_insight(
            'loja', 'Estoque baixo na loja',
            f'{estoque_baixo} produto(s) com 5 unidades ou menos.',
            prioridade='media',
            acao='Gestão loja',
            acao_url=reverse('loja_gestao'),
        ))

    passeios = Passeio.objects.filter(hotel=hotel, dia_semana=dia_semana, ativo=True).count()
    if passeios and hospedes_ativos > 10:
        insights.append(_insight(
            'passeio', 'Passeios disponíveis hoje',
            f'{passeios} passeio(s) ativo(s). Divulgue no app do hóspede.',
            prioridade='baixa',
            acao='App hóspede',
            acao_url=reverse('hospede_app_login'),
        ))

    try:
        cruz = cruzar_banco(hotel, dias=30)
        if cruz.total_linhas >= 10:
            for faixa in cruz.faixas:
                if faixa.total_linhas == 0 and hospedes_ativos > 5:
                    insights.append(_insight(
                        'faixa', f'Faixa {faixa.label} sem histórico',
                        'Nos últimos 30 dias não houve atividades registradas para esta faixa.',
                        prioridade='baixa',
                        acao='Análise faixas',
                        acao_url=reverse('analise_faixas'),
                    ))
                    break
    except Exception:
        pass

    if not insights:
        insights.append(_insight(
            'ok', 'Operação equilibrada',
            'Nenhum alerta crítico detectado para hoje. Continue monitorando o dashboard.',
            prioridade='baixa',
            acao='Dashboard executivo',
            acao_url=reverse('dashboard_executivo'),
        ))

    ordem = {'alta': 0, 'media': 1, 'baixa': 2}
    insights.sort(key=lambda i: ordem.get(i['prioridade'], 9))
    return insights[:8]
