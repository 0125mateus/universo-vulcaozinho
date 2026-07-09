"""Gerador de payload PIX (BR Code / EMV) estático para "copia e cola".

Sem dependências externas. Gera a string que pode ser copiada no app do banco
ou transformada em QR Code.
"""

import re
import unicodedata


def _sanitizar(texto: str, limite: int) -> str:
    if not texto:
        return ''
    normalizado = unicodedata.normalize('NFKD', texto)
    ascii_txt = normalizado.encode('ascii', 'ignore').decode('ascii')
    ascii_txt = re.sub(r'[^A-Za-z0-9 ]', '', ascii_txt).upper().strip()
    return ascii_txt[:limite]


def _campo(id_campo: str, valor: str) -> str:
    return f'{id_campo}{len(valor):02d}{valor}'


def _crc16(payload: str) -> str:
    polinomio = 0x1021
    resultado = 0xFFFF
    for byte in payload.encode('utf-8'):
        resultado ^= byte << 8
        for _ in range(8):
            if resultado & 0x8000:
                resultado = (resultado << 1) ^ polinomio
            else:
                resultado <<= 1
            resultado &= 0xFFFF
    return format(resultado, '04X')


def gerar_payload_pix(chave, nome_beneficiario, cidade='POCOS DE CALDAS', valor=None, txid='***'):
    """Monta o payload PIX estático (copia e cola).

    - chave: chave PIX (CPF/CNPJ/email/telefone/aleatória)
    - valor: Decimal/float/str opcional (se None, gera sem valor definido)
    - txid: identificador da transação (máx 25 chars alfanuméricos)
    """
    if not chave:
        return ''

    nome = _sanitizar(nome_beneficiario or 'BENEFICIARIO', 25) or 'BENEFICIARIO'
    cidade_fmt = _sanitizar(cidade or 'CIDADE', 15) or 'CIDADE'
    txid_fmt = re.sub(r'[^A-Za-z0-9]', '', str(txid or '***')) or '***'
    txid_fmt = txid_fmt[:25]

    merchant_account = _campo('00', 'br.gov.bcb.pix') + _campo('01', str(chave))
    payload = (
        _campo('00', '01')
        + _campo('26', merchant_account)
        + _campo('52', '0000')
        + _campo('53', '986')
    )

    if valor is not None:
        try:
            valor_fmt = f'{float(valor):.2f}'
            payload += _campo('54', valor_fmt)
        except (TypeError, ValueError):
            pass

    payload += (
        _campo('58', 'BR')
        + _campo('59', nome)
        + _campo('60', cidade_fmt)
        + _campo('62', _campo('05', txid_fmt))
    )

    payload += '6304'
    payload += _crc16(payload)
    return payload
