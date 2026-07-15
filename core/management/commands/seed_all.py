from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Executa todos os seeds na ordem correta (idempotente).'

    SEEDS = [
        'seed_hoteis',
        'seed_categorias',
        'seed_noites_tematicas',
        'seed_programacao',
        'seed_passeios',
        'seed_loja',
        'seed_salas_reuniao',
        'seed_superuser',
        'seed_usuarios_demo',
        'seed_ponto',
    ]

    def handle(self, *args, **options):
        for cmd in self.SEEDS:
            self.stdout.write(self.style.MIGRATE_HEADING(f'→ {cmd}'))
            call_command(cmd)
        self.stdout.write(self.style.SUCCESS('\nTodos os seeds concluídos.'))
