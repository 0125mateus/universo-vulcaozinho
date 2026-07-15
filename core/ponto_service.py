"""Serviço de ponto eletrônico dos recreadores."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils import timezone

from .models import Hotel, PontoBatida, Recreador, TipoPontoBatida

ANTI_DOUBLE_TAP = timedelta(seconds=60)


class PontoErro(Exception):
    """Erro de negócio no ponto."""


@dataclass
class EstadoPonto:
    proxima_acao: str  # 'entrada' | 'saida'
    entrada_aberta: PontoBatida | None
    ultima_batida: PontoBatida | None


def _dia_local_bounds(agora: datetime | None = None):
    agora = agora or timezone.now()
    hoje = timezone.localdate(agora)
    inicio = timezone.make_aware(datetime.combine(hoje, datetime.min.time()))
    fim = inicio + timedelta(days=1)
    return hoje, inicio, fim


def estado_ponto_hoje(recreador: Recreador, agora: datetime | None = None) -> EstadoPonto:
    _, inicio, fim = _dia_local_bounds(agora)
    batidas = list(
        PontoBatida.objects.filter(
            recreador=recreador,
            registrado_em__gte=inicio,
            registrado_em__lt=fim,
        ).order_by('registrado_em')
    )
    ultima = batidas[-1] if batidas else None
    entrada_aberta = None
    for b in reversed(batidas):
        if b.tipo == TipoPontoBatida.SAIDA:
            break
        if b.tipo == TipoPontoBatida.ENTRADA:
            entrada_aberta = b
            break
    proxima = TipoPontoBatida.SAIDA if entrada_aberta else TipoPontoBatida.ENTRADA
    return EstadoPonto(proxima_acao=proxima, entrada_aberta=entrada_aberta, ultima_batida=ultima)


def normalizar_nome(nome: str) -> str:
    return ' '.join((nome or '').split()).strip()


def buscar_recreador_por_nome(hotel: Hotel, nome: str) -> Recreador:
    nome_limpo = normalizar_nome(nome)
    if len(nome_limpo) < 2:
        raise PontoErro('Informe seu nome completo (como no cadastro).')
    qs = Recreador.objects.filter(hotel=hotel, ativo=True, nome__iexact=nome_limpo)
    count = qs.count()
    if count == 0:
        raise PontoErro('Nome não encontrado neste hotel. Confira a grafia ou fale com a gerência.')
    if count > 1:
        raise PontoErro('Há mais de um recreador com esse nome. Use o tablet da sala ou fale com a gerência.')
    return qs.get()


def autenticar_por_nome_pin(hotel: Hotel, nome: str, pin: str) -> Recreador:
    recreador = buscar_recreador_por_nome(hotel, nome)
    validar_pin(recreador, pin)
    return recreador


def validar_pin(recreador: Recreador, pin: str) -> None:
    if not recreador.ativo:
        raise PontoErro('Recreador inativo.')
    if not recreador.tem_pin:
        raise PontoErro('PIN ainda não configurado. Procure a gerência.')
    if not recreador.check_pin(pin):
        raise PontoErro('PIN incorreto.')


@transaction.atomic
def registrar_batida(
    *,
    recreador: Recreador,
    hotel: Hotel,
    pin: str | None = None,
    tipo: str | None = None,
    extra_plantao: bool = False,
    foto_auditoria: UploadedFile | None = None,
    ip: str | None = None,
    user_agent: str = '',
    registrado_por=None,
    agora: datetime | None = None,
    exigir_pin: bool = True,
) -> PontoBatida:
    if exigir_pin:
        validar_pin(recreador, pin or '')
    elif not recreador.ativo:
        raise PontoErro('Recreador inativo.')
    if recreador.hotel_id != hotel.id:
        raise PontoErro('Recreador não pertence a este hotel.')

    agora = agora or timezone.now()
    estado = estado_ponto_hoje(recreador, agora)
    tipo_final = tipo or estado.proxima_acao
    if tipo_final not in {TipoPontoBatida.ENTRADA, TipoPontoBatida.SAIDA}:
        raise PontoErro('Tipo de batida inválido.')

    if tipo_final != estado.proxima_acao:
        esperado = 'Entrada' if estado.proxima_acao == TipoPontoBatida.ENTRADA else 'Saída'
        raise PontoErro(f'Próxima batida esperada: {esperado}.')

    if estado.ultima_batida and (agora - estado.ultima_batida.registrado_em) < ANTI_DOUBLE_TAP:
        raise PontoErro('Aguarde um minuto antes de bater o ponto novamente.')

    batida = PontoBatida(
        hotel=hotel,
        recreador=recreador,
        tipo=tipo_final,
        extra_plantao=bool(extra_plantao),
        registrado_em=agora,
        ip=ip or None,
        user_agent=(user_agent or '')[:255],
        registrado_por=registrado_por,
    )
    if foto_auditoria:
        batida.foto_auditoria = foto_auditoria
    batida.save()
    return batida
