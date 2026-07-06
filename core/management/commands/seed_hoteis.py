from django.core.management.base import BaseCommand

from core.models import Hotel, RedeMarca


# Paletas extraídas dos uniformes 2025 — Time da Recreação Poços de Caldas
HOTEIS_REDE = [
    {
        'nome': 'Nacional Inn Poços de Caldas',
        'slug': 'nacional-inn',
        'rede_marca': RedeMarca.NACIONAL_INN,
        'slogan': 'Energia da diversão! A diversão começa aqui!',
        # Verde floresta + limão + laranja + amarelo + ciano (uniforme regata/camiseta)
        'cor_primaria': '#006838',
        'cor_secundaria': '#8DC63F',
        'cor_destaque': '#FFED00',
        'cor_terciaria': '#F7941D',
    },
    {
        'nome': 'Euro Suite Hotel',
        'slug': 'euro-suite',
        'rede_marca': RedeMarca.EURO_SUITE,
        'slogan': 'Time da Alegria! Missão: fazer você sorrir!',
        # Vinho/bordô + magenta + laranja + amarelo
        'cor_primaria': '#6B1C2F',
        'cor_secundaria': '#ED1E79',
        'cor_destaque': '#FFED00',
        'cor_terciaria': '#F7941D',
    },
    {
        'nome': 'Dan Inn Poços de Caldas',
        'slug': 'dan-inn',
        'rede_marca': RedeMarca.DAN_INN,
        'slogan': 'A diversão não tem limites! Espalhando sorrisos por onde passamos!',
        # Navy + royal blue + ciano + laranja + amarelo
        'cor_primaria': '#002855',
        'cor_secundaria': '#0072BC',
        'cor_destaque': '#FFED00',
        'cor_terciaria': '#00AEEF',
    },
]


class Command(BaseCommand):
    help = 'Cadastra os três hotéis da rede Universo Vulcãozinho (idempotente).'

    def handle(self, *args, **options):
        for dados in HOTEIS_REDE:
            slug = dados.pop('slug')
            hotel, created = Hotel.objects.update_or_create(
                slug=slug,
                defaults={
                    **dados,
                    'cidade': 'Poços de Caldas',
                    'estado': 'MG',
                    'ativo': True,
                },
            )
            acao = 'Criado' if created else 'Atualizado'
            self.stdout.write(self.style.SUCCESS(f'{acao}: {hotel.nome}'))

        self.stdout.write(self.style.SUCCESS('Seed de hotéis concluída.'))
