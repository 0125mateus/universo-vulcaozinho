"""Aprendizado simples a partir das consultas dos usuários."""

import re
from django.db.models import Q
from collections import Counter

from core.models import ConsultaAssistente


def _normalizar(texto: str) -> str:
    t = (texto or '').lower().strip()
    t = re.sub(r'\s+', ' ', t)
    return t[:500]


def _tags_da_mensagem(mensagem: str) -> list[str]:
    t = _normalizar(mensagem)
    mapa = [
        ('programacao', r'programa|grade|hor[aá]rio|atividade'),
        ('hospede', r'h[oó]spede|check-in|checkin|apartamento'),
        ('passeio', r'passeio|pix|pagamento'),
        ('passaporte', r'passaporte|carimbo|moeda'),
        ('ponto', r'ponto|batida|recreador|rh'),
        ('loja', r'loja|pdv|venda|estoque'),
        ('faixa', r'faixa|idade|ages'),
        ('dashboard', r'dashboard|kpi|ocupa'),
        ('telao', r'tel[aã]o|tv'),
        ('financeiro', r'financeiro|pagamento|extra'),
    ]
    tags = [nome for nome, pat in mapa if re.search(pat, t)]
    return tags or ['geral']


def registrar_consulta(*, hotel, usuario, canal, mensagem, resposta, fonte='guided'):
    ConsultaAssistente.objects.create(
        hotel=hotel,
        usuario=usuario if usuario and usuario.is_authenticated else None,
        canal=canal,
        mensagem=_normalizar(mensagem),
        resposta_resumo=(resposta or '')[:800],
        tags=','.join(_tags_da_mensagem(mensagem)),
        fonte=fonte,
    )


def sugestoes_aprendidas(hotel, limite=4) -> list[str]:
    """Perguntas frequentes reais dos usuários deste hotel (ou rede)."""
    qs = ConsultaAssistente.objects.filter(canal='staff')
    if hotel:
        qs = qs.filter(Q(hotel=hotel) | Q(hotel__isnull=True))
    recentes = qs.order_by('-criado_em')[:200]
    counter = Counter()
    for c in recentes:
        if len(c.mensagem) >= 8:
            counter[c.mensagem] += 1
    return [msg.capitalize() if msg[0].islower() else msg for msg, _ in counter.most_common(limite)]


def resumo_aprendizado(hotel) -> str:
    """Texto curto sobre padrões recentes — vai para o prompt da IA."""
    qs = ConsultaAssistente.objects.filter(canal='staff')
    if hotel:
        qs = qs.filter(hotel=hotel)
    tags = Counter()
    for t in qs.order_by('-criado_em')[:80].values_list('tags', flat=True):
        for tag in (t or '').split(','):
            if tag:
                tags[tag] += 1
    if not tags:
        return ''
    top = ', '.join(f'{k} ({v})' for k, v in tags.most_common(5))
    return f'Temas mais perguntados pela equipe recentemente: {top}.'
