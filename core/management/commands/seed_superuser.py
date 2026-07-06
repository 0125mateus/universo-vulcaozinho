from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Cria superusuário de teste (admin / admin) — idempotente.'

    def handle(self, *args, **options):
        User = get_user_model()
        user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@teste.local',
                'is_staff': True,
                'is_superuser': True,
            },
        )
        user.set_password('admin')
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.save()

        acao = 'Criado' if created else 'Atualizado'
        self.stdout.write(self.style.SUCCESS(f'{acao}: admin / admin (somente para testes)'))
