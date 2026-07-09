"""Montagem da grade de programação para telão e páginas públicas."""

from __future__ import annotations

from django.utils import timezone

from .models import CategoriaProgramacao, Hotel, ProgramacaoDiaria


def _serializar_atividade(prog: ProgramacaoDiaria) -> dict:
    cat = prog.categoria
    return {
        'id': prog.pk,
        'hora_inicio': prog.hora_inicio.strftime('%H:%M'),
        'hora_fim': prog.hora_fim.strftime('%H:%M'),
        'nome': prog.atividade.nome,
        'icone': prog.atividade.icone or '⭐',
        'local': prog.local.nome if prog.local else '',
        'recreador': prog.recreador.nome if prog.recreador else '',
        'faixa': cat.nome if cat else 'Geral',
        'faixa_icone': cat.icone if cat else '📋',
        'faixa_cor': cat.cor if cat else '#888888',
    }


def montar_grade_hotel(hotel: Hotel, data=None) -> dict:
    """Grade por faixa (mesma lógica da página /programacao/)."""
    data = data or timezone.localdate()
    categorias = list(CategoriaProgramacao.objects.all())
    programacoes = list(
        ProgramacaoDiaria.objects.filter(hotel=hotel, data=data)
        .select_related('atividade', 'local', 'categoria', 'recreador')
        .order_by('hora_inicio')
    )

    grade = {cat.id: [] for cat in categorias}
    sem_categoria = []
    for prog in programacoes:
        if prog.categoria_id and prog.categoria_id in grade:
            grade[prog.categoria_id].append(prog)
        else:
            sem_categoria.append(prog)

    colunas = []
    itens = []
    for cat in categorias:
        progs = grade.get(cat.id, [])
        atividades = [_serializar_atividade(p) for p in progs]
        colunas.append({
            'faixa': cat.nome,
            'faixa_icone': cat.icone,
            'faixa_cor': cat.cor,
            'idade_min': cat.idade_min,
            'idade_max': cat.idade_max,
            'atividades': atividades,
        })
        itens.extend(atividades)

    for prog in sem_categoria:
        item = _serializar_atividade(prog)
        itens.append(item)

    if sem_categoria:
        colunas.append({
            'faixa': 'Outras',
            'faixa_icone': '📋',
            'faixa_cor': '#888888',
            'idade_min': None,
            'idade_max': None,
            'atividades': [_serializar_atividade(p) for p in sem_categoria],
        })

    itens.sort(key=lambda x: x['hora_inicio'])
    return {
        'data': data.isoformat(),
        'total': len(programacoes),
        'colunas': colunas,
        'itens': itens,
    }
