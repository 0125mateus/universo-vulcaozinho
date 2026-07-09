"""Hotéis oficiais da rede Vulcãozinho."""

from .models import Hotel

HOTEIS_REDE_SLUGS = (
    'dan-inn',
    'euro-suite',
    'nacional-inn',
)


def hoteis_rede_queryset():
    """Apenas os três hotéis da rede (exclui registros de teste)."""
    return Hotel.objects.filter(ativo=True, slug__in=HOTEIS_REDE_SLUGS).order_by('nome')
