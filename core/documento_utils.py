"""Formatação e normalização de documentos (CPF, CNPJ, RG, passaporte)."""

from __future__ import annotations

import re

_DIGITOS = re.compile(r'\D')
_ALFANUM = re.compile(r'[^a-zA-Z0-9]')


def digitos(valor: str) -> str:
    return _DIGITOS.sub('', valor or '')


def normalizar_documento(valor: str) -> str:
    """Chave para comparação — dígitos (CPF/CNPJ/RG) ou alfanumérico (passaporte)."""
    valor = (valor or '').strip()
    if not valor:
        return ''
    limpo = digitos(valor)
    if len(limpo) in (11, 14):
        return limpo
    return _ALFANUM.sub('', valor).upper()


def formatar_documento(valor: str) -> str:
    """Aplica máscara brasileira quando reconhecível."""
    valor = (valor or '').strip()
    if not valor:
        return ''

    limpo = digitos(valor)
    if len(limpo) == 11:
        return f'{limpo[:3]}.{limpo[3:6]}.{limpo[6:9]}-{limpo[9:11]}'
    if len(limpo) == 14:
        return (
            f'{limpo[:2]}.{limpo[2:5]}.{limpo[5:8]}/'
            f'{limpo[8:12]}-{limpo[12:14]}'
        )
    if len(limpo) == 9:
        return f'{limpo[:2]}.{limpo[2:5]}.{limpo[5:8]}-{limpo[8]}'
    if len(limpo) == 8:
        return f'{limpo[0]}.{limpo[1:4]}.{limpo[4:7]}-{limpo[7]}'
    if len(limpo) == 7:
        return f'{limpo[:2]}.{limpo[2:5]}.{limpo[5:7]}'

    alnum = _ALFANUM.sub('', valor).upper()
    return alnum if alnum else valor


def documento_duplicado_ativo(hotel, documento: str, *, exclude_pk=None) -> bool:
    from .models import Hospede

    chave = normalizar_documento(documento)
    if not chave:
        return False

    qs = Hospede.objects.filter(hotel=hotel, data_checkout__isnull=True)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)

    for hospede in qs.only('pk', 'documento'):
        if normalizar_documento(hospede.documento) == chave:
            return True
    return False
