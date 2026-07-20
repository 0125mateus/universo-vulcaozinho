"""Logos oficiais dos hotéis da rede."""

HOTEIS_COM_LOGO = frozenset({
    'cassino-resort',
    'dan-inn',
    'euro-suite',
    'nacional-inn',
})

FALLBACK_LOGO = 'img/mascote-recrear.svg'


def hotel_logo_static_path(slug: str | None) -> str:
    if slug and slug in HOTEIS_COM_LOGO:
        return f'img/hoteis/{slug}.png'
    return FALLBACK_LOGO
