from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from core.models import Hotel, PapelUsuario, PerfilUsuario


User = get_user_model()

USUARIOS_DEMO = [
    {
        'username': 'admin_rede',
        'email': 'admin@vulcaozinho.local',
        'papel': PapelUsuario.ADMIN,
        'hotel': None,
        'is_staff': True,
        'is_superuser': False,
    },
    {
        'username': 'diretor_rede',
        'email': 'diretor@vulcaozinho.local',
        'papel': PapelUsuario.DIRETOR,
        'hotel': None,
        'is_staff': True,
    },
    {
        'username': 'gerente_nacional',
        'email': 'gerente.nacional@vulcaozinho.local',
        'papel': PapelUsuario.GERENTE,
        'hotel_slug': 'nacional-inn',
        'is_staff': True,
    },
    {
        'username': 'supervisor_nacional',
        'email': 'supervisor.nacional@vulcaozinho.local',
        'papel': PapelUsuario.SUPERVISOR,
        'hotel_slug': 'nacional-inn',
        'is_staff': True,
    },
    {
        'username': 'recreador_nacional',
        'email': 'recreador.nacional@vulcaozinho.local',
        'papel': PapelUsuario.RECREADOR,
        'hotel_slug': 'nacional-inn',
        'is_staff': True,
    },
    {
        'username': 'recepcao_nacional',
        'email': 'recepcao.nacional@vulcaozinho.local',
        'papel': PapelUsuario.RECEPCAO,
        'hotel_slug': 'nacional-inn',
        'is_staff': True,
    },
    {
        'username': 'restaurante_nacional',
        'email': 'restaurante.nacional@vulcaozinho.local',
        'papel': PapelUsuario.RESTAURANTE,
        'hotel_slug': 'nacional-inn',
        'is_staff': True,
    },
    {
        'username': 'loja_nacional',
        'email': 'loja.nacional@vulcaozinho.local',
        'papel': PapelUsuario.LOJA,
        'hotel_slug': 'nacional-inn',
        'is_staff': True,
    },
]

SENHA_PADRAO = 'vulcaozinho123'


class Command(BaseCommand):
    help = 'Cria usuários demo por papel (senha: vulcaozinho123) — idempotente.'

    def handle(self, *args, **options):
        for dados in USUARIOS_DEMO:
            d = dict(dados)
            username = d['username']
            hotel_slug = d.pop('hotel_slug', None)
            papel = d.pop('papel')
            hotel = Hotel.objects.filter(slug=hotel_slug).first() if hotel_slug else None

            user, created = User.objects.update_or_create(
                username=username,
                defaults={
                    'email': d.get('email', ''),
                    'is_staff': d.get('is_staff', False),
                    'is_superuser': d.get('is_superuser', False),
                    'is_active': True,
                },
            )
            user.set_password(SENHA_PADRAO)
            user.save()

            perfil, _ = PerfilUsuario.objects.update_or_create(
                user=user,
                defaults={'hotel': hotel, 'papel': papel, 'ativo': True},
            )

            grupo = Group.objects.filter(name=f'vulcaozinho_{papel}').first()
            if grupo:
                user.groups.set([grupo])

            acao = 'Criado' if created else 'Atualizado'
            self.stdout.write(self.style.SUCCESS(
                f'{acao}: {username} / {SENHA_PADRAO} — {papel}'
            ))

        self.stdout.write(self.style.SUCCESS(
            f'\nTodos os usuários demo usam senha: {SENHA_PADRAO}'
        ))
        self.stdout.write('Teste login em: /entrar/')
