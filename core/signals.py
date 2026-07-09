"""Sinais que disparam atualização em tempo real (WebSocket)."""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import (
    CarimboPassaporte,
    Hospede,
    InscricaoAtividade,
    Passeio,
    PassaporteHospede,
    PresencaRegistro,
    ProdutoLoja,
    ProgramacaoDiaria,
    EventoRecreacao,
    VendaLoja,
)
from .realtime import broadcast_all_hotels, broadcast_hotel_update


def _hotel_id_hospede(hospede) -> int | None:
    return hospede.hotel_id if hospede else None


def _hotel_id_programacao(programacao) -> int | None:
    return programacao.hotel_id if programacao else None


@receiver(post_save, sender=Hospede)
@receiver(post_delete, sender=Hospede)
def on_hospede_change(sender, instance, **kwargs):
    broadcast_hotel_update(instance.hotel_id)


@receiver(post_save, sender=ProgramacaoDiaria)
@receiver(post_delete, sender=ProgramacaoDiaria)
def on_programacao_change(sender, instance, **kwargs):
    broadcast_hotel_update(instance.hotel_id)


@receiver(post_save, sender=PresencaRegistro)
@receiver(post_delete, sender=PresencaRegistro)
def on_presenca_change(sender, instance, **kwargs):
    broadcast_hotel_update(_hotel_id_programacao(instance.programacao))


@receiver(post_save, sender=InscricaoAtividade)
@receiver(post_delete, sender=InscricaoAtividade)
def on_inscricao_change(sender, instance, **kwargs):
    broadcast_hotel_update(_hotel_id_programacao(instance.programacao))


@receiver(post_save, sender=PassaporteHospede)
@receiver(post_delete, sender=PassaporteHospede)
def on_passaporte_change(sender, instance, **kwargs):
    broadcast_hotel_update(_hotel_id_hospede(instance.hospede))


@receiver(post_save, sender=CarimboPassaporte)
@receiver(post_delete, sender=CarimboPassaporte)
def on_carimbo_change(sender, instance, **kwargs):
    broadcast_hotel_update(_hotel_id_hospede(instance.passaporte.hospede))


@receiver(post_save, sender=Passeio)
@receiver(post_delete, sender=Passeio)
def on_passeio_change(sender, instance, **kwargs):
    broadcast_hotel_update(instance.hotel_id)


@receiver(post_save, sender=ProdutoLoja)
@receiver(post_delete, sender=ProdutoLoja)
def on_produto_change(sender, instance, **kwargs):
    if instance.hotel_id:
        broadcast_hotel_update(instance.hotel_id)
    else:
        broadcast_all_hotels()


@receiver(post_save, sender=VendaLoja)
@receiver(post_delete, sender=VendaLoja)
def on_venda_change(sender, instance, **kwargs):
    broadcast_hotel_update(instance.hotel_id)


@receiver(post_save, sender=EventoRecreacao)
@receiver(post_delete, sender=EventoRecreacao)
def on_evento_change(sender, instance, **kwargs):
    broadcast_hotel_update(instance.hotel_id)
