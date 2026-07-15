from django.core.management.base import BaseCommand

from core.models import Recreador

PIN_DEMO = '1234'


class Command(BaseCommand):
    help = f'Define PIN demo ({PIN_DEMO}) em recreadores sem PIN (idempotente).'

    def handle(self, *args, **options):
        qs = Recreador.objects.filter(pin_hash='')
        count = 0
        for r in qs:
            r.set_pin(PIN_DEMO)
            r.save(update_fields=['pin_hash', 'pin_atualizado_em'])
            count += 1
        self.stdout.write(self.style.SUCCESS(
            f'PIN {PIN_DEMO} definido em {count} recreador(es). '
            f'Total com PIN: {Recreador.objects.exclude(pin_hash="").count()}'
        ))
