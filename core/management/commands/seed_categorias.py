from django.core.management.base import BaseCommand

from core.models import CategoriaProgramacao


CATEGORIAS = [
    {
        'codigo': 'vulcao-kids',
        'nome': 'Vulcão Kids',
        'idade_min': 7,
        'idade_max': 12,
        'cor': '#E67E22',
        'icone': '🌋',
        'ordem': 1,
        'descricao_atividades': (
            'Jogos, piscina kids, oficinas, mini disco, caça ao tesouro, hora do conto, '
            'pintura, brincadeiras em grupo e atividades lúdicas.'
        ),
    },
    {
        'codigo': 'boys-girls',
        'nome': 'Boys & Girls',
        'idade_min': 13,
        'idade_max': 17,
        'cor': '#2980B9',
        'icone': '🎵',
        'ordem': 2,
        'descricao_atividades': (
            'Esportes, gincanas, desafios, torneios, karaokê, dança, gaming, '
            'competições e atividades de integração.'
        ),
    },
    {
        'codigo': 'adultos',
        'nome': 'Adultos',
        'idade_min': 18,
        'idade_max': 59,
        'cor': '#27AE60',
        'icone': '⭐',
        'ordem': 3,
        'descricao_atividades': (
            'Alongamento, hidroginástica, vôlei, beach tennis, aulas, degustações, '
            'shows, caminhadas e atividades de bem-estar.'
        ),
    },
    {
        'codigo': 'melhor-idade',
        'nome': 'Melhor Idade',
        'idade_min': 60,
        'idade_max': 120,
        'cor': '#8E44AD',
        'icone': '💜',
        'ordem': 4,
        'descricao_atividades': (
            'Caminhadas, alongamento, jogos de salão, tarde da prosa, aulas leves, '
            'música ao vivo, bingo e momentos de convivência.'
        ),
    },
]


class Command(BaseCommand):
    help = 'Cadastra faixas etárias da recreação (Ages) — idempotente.'

    def handle(self, *args, **options):
        for dados in CATEGORIAS:
            codigo = dados.pop('codigo')
            cat, created = CategoriaProgramacao.objects.update_or_create(
                codigo=codigo,
                defaults=dados,
            )
            acao = 'Criado' if created else 'Atualizado'
            self.stdout.write(self.style.SUCCESS(f'{acao}: {cat.nome} ({cat.faixa_label})'))

        self.stdout.write(self.style.SUCCESS('Seed de faixas etárias concluída.'))
