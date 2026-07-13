from django.core.management.base import BaseCommand

from core.models import Hotel, SalaReuniao


SALAS = [
    {
        'nome': 'Diretoria — Rede Vulcãozinho',
        'slug': 'diretoria-rede',
        'hotel': None,
        'descricao': 'Reunião geral entre diretores dos hotéis da rede.',
    },
    {
        'nome': 'Diretoria — Cassino Resort',
        'slug': 'diretoria-cassino-resort',
        'hotel_slug': 'cassino-resort',
        'descricao': 'Sala de reunião do Cassino All Inclusive Resort.',
    },
    {
        'nome': 'Diretoria — Nacional Inn',
        'slug': 'diretoria-nacional-inn',
        'hotel_slug': 'nacional-inn',
        'descricao': 'Sala de reunião do Nacional Inn Poços de Caldas.',
    },
    {
        'nome': 'Diretoria — Euro Suite',
        'slug': 'diretoria-euro-suite',
        'hotel_slug': 'euro-suite',
        'descricao': 'Sala de reunião do Euro Suite Hotel.',
    },
    {
        'nome': 'Diretoria — Dan Inn',
        'slug': 'diretoria-dan-inn',
        'hotel_slug': 'dan-inn',
        'descricao': 'Sala de reunião do Dan Inn Poços de Caldas.',
    },
]


class Command(BaseCommand):
    help = 'Cadastra salas de reunião para diretores (idempotente).'

    def handle(self, *args, **options):
        for dados in SALAS:
            hotel_slug = dados.pop('hotel_slug', None)
            slug = dados.pop('slug')
            hotel = None
            if hotel_slug:
                hotel = Hotel.objects.filter(slug=hotel_slug).first()

            sala, created = SalaReuniao.objects.update_or_create(
                slug=slug,
                defaults={**dados, 'hotel': hotel, 'ativa': True},
            )
            acao = 'Criada' if created else 'Atualizada'
            self.stdout.write(self.style.SUCCESS(f'{acao}: {sala.nome}'))

        self.stdout.write(self.style.SUCCESS('Salas de reunião prontas.'))
