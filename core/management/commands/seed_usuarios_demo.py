from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from core.models import Hotel, PapelUsuario, PerfilUsuario


User = get_user_model()

SENHA_PADRAO = 'vulcaozinho123'

# Usuários com acesso à rede inteira (podem trocar de hotel)
USUARIOS_REDE = [
    {
        'username': 'admin_rede',
        'email': 'admin@vulcaozinho.local',
        'papel': PapelUsuario.ADMIN,
        'is_staff': True,
    },
    {
        'username': 'diretor_rede',
        'email': 'diretor@vulcaozinho.local',
        'papel': PapelUsuario.DIRETOR,
        'is_staff': True,
    },
]

# Papéis criados por hotel (username: {papel}_{sufixo})
PAPEIS_HOTEL = [
    ('gerente', PapelUsuario.GERENTE),
    ('supervisor', PapelUsuario.SUPERVISOR),
    ('recreador', PapelUsuario.RECREADOR),
    ('recepcao', PapelUsuario.RECEPCAO),
    ('restaurante', PapelUsuario.RESTAURANTE),
    ('loja', PapelUsuario.LOJA),
]

HOTEIS_DEMO = [
    ('nacional', 'nacional-inn'),
    ('euro', 'euro-suite'),
    ('dan', 'dan-inn'),
]


def _usuarios_por_hotel():
    usuarios = []
    for sufixo, slug in HOTEIS_DEMO:
        for papel_username, papel in PAPEIS_HOTEL:
            username = f'{papel_username}_{sufixo}'
            usuarios.append({
                'username': username,
                'email': f'{username}@vulcaozinho.local',
                'papel': papel,
                'hotel_slug': slug,
                'is_staff': True,
            })
    return usuarios


USUARIOS_DEMO = USUARIOS_REDE + _usuarios_por_hotel()


class Command(BaseCommand):
    help = 'Cria usuários demo por papel e hotel (senha: vulcaozinho123) — idempotente.'

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

            PerfilUsuario.objects.update_or_create(
                user=user,
                defaults={'hotel': hotel, 'papel': papel, 'ativo': True},
            )

            grupo = Group.objects.filter(name=f'vulcaozinho_{papel}').first()
            if grupo:
                user.groups.set([grupo])

            hotel_label = hotel.nome if hotel else 'rede inteira'
            acao = 'Criado' if created else 'Atualizado'
            self.stdout.write(self.style.SUCCESS(
                f'{acao}: {username} / {SENHA_PADRAO} — {papel} ({hotel_label})'
            ))

        self.stdout.write(self.style.SUCCESS(
            f'\nTodos os usuários demo usam senha: {SENHA_PADRAO}'
        ))
        self.stdout.write('Teste login em: /entrar/')
