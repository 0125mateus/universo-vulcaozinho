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
        if created:
            user.set_password('admin')
            user.save()
            self.stdout.write(self.style.SUCCESS('Criado: admin / admin (somente para testes)'))
        else:
            self.stdout.write('admin já existe — senha não alterada.')
