from django.core.management.base import BaseCommand

from core.models import DiaSemana, Hotel, NoiteTematica


NOITES = [
    {
        'dia_semana': DiaSemana.SEGUNDA,
        'tema': 'Cores',
        'cor_dominante': 'Multicolor',
        'cores_do_dia': 'Azul, Verde, Amarelo, Vermelho',
        'atracao_musical': 'MPB',
        'vista_se': 'Roupas coloridas',
        'descricao_gastronomia': (
            'Frutas tropicais, espetinhos, tapiocas, sucos naturais, sorvetes'
        ),
        'manha_tema': 'Manhã Tropical (MPB leve e bossa nova)',
        'manha_genero_musical': 'MPB leve e bossa nova',
        'manha_atividades': (
            'Alongamento, dança, boas-vindas, degustação de frutas tropicais'
        ),
    },
    {
        'dia_semana': DiaSemana.TERCA,
        'tema': 'Black Night',
        'cor_dominante': 'Preto',
        'cores_do_dia': 'Preto, Cinza, Branco',
        'atracao_musical': 'Black Music',
        'vista_se': 'Roupas totalmente pretas',
        'descricao_gastronomia': (
            'Hambúrguer gourmet, costela, barbecue, batata rústica, brownie, milk shake oreo'
        ),
        'manha_tema': 'Black Energy (Soul, Black Music, R&B)',
        'manha_genero_musical': 'Soul, Black Music, R&B',
        'manha_atividades': 'Desafio fitness, dança, jogos e muita energia',
    },
    {
        'dia_semana': DiaSemana.QUARTA,
        'tema': 'Golden Night',
        'cor_dominante': 'Dourado',
        'cores_do_dia': 'Dourado, Amarelo, Laranja',
        'atracao_musical': 'Golden Hits (sucessos de 60 a 2010)',
        'vista_se': 'Roupas douradas',
        'descricao_gastronomia': (
            'Risotos, massas, queijos, salmão, camarões, quindim, drinks dourados'
        ),
        'manha_tema': 'Golden Morning (Flashbacks internacionais)',
        'manha_genero_musical': 'Flashbacks internacionais',
        'manha_atividades': 'Café especial, fotos temáticas, jogos, brindes dourados',
    },
    {
        'dia_semana': DiaSemana.QUINTA,
        'tema': 'Brasilidades (Noite Livre)',
        'cor_dominante': 'Livre',
        'cores_do_dia': 'Roxo, Rosa, Laranja, Amarelo',
        'atracao_musical': 'Pop Hits / Top Hits atuais',
        'vista_se': 'Livre, à vontade',
        'descricao_gastronomia': (
            'Sabores do Brasil: pastéis, coxinhas, pão de queijo, caldos, cocada, paçoca'
        ),
        'manha_tema': 'Brasilidades (Forró, Pop nacional, Axé)',
        'manha_genero_musical': 'Forró, Pop nacional, Axé',
        'manha_atividades': 'Gincanas, oficinas, brincadeiras típicas e muita animação',
    },
    {
        'dia_semana': DiaSemana.SEXTA,
        'tema': 'Moda de Viola (Sertanejo)',
        'cor_dominante': 'Marrom',
        'cores_do_dia': 'Marrom, Bege, Verde escuro',
        'atracao_musical': 'Moda de viola sertanejo para todos',
        'vista_se': 'Estilo sertanejo',
        'descricao_gastronomia': (
            'Feijão tropeiro, costela, linguiça, milho, mandioca, doce de leite e curau'
        ),
        'manha_tema': 'Raízes do Interior (Moda de viola, sertanejo)',
        'manha_genero_musical': 'Moda de viola, sertanejo',
        'manha_atividades': 'Café caipira, brincadeiras rurais tiro ao alvo, muita prosa',
    },
    {
        'dia_semana': DiaSemana.SABADO,
        'tema': 'Festa Neon',
        'cor_dominante': 'Neon',
        'cores_do_dia': 'Rosa neon, Verde neon, Azul neon, Laranja neon',
        'atracao_musical': 'Flashback anos 70, 80 e 90',
        'vista_se': 'Roupas neon',
        'descricao_gastronomia': (
            'Pizzas, petiscos, drinks coloridos, açaí, picolés, frutas geladas'
        ),
        'manha_tema': 'Praia & Piscina (Reggae, Surf music, Pop)',
        'manha_genero_musical': 'Reggae, Surf music, Pop',
        'manha_atividades': 'Hidro recreativa, dança, jogos na piscina, festa da espuma',
    },
    {
        'dia_semana': DiaSemana.DOMINGO,
        'tema': 'White Family',
        'cor_dominante': 'Branco',
        'cores_do_dia': 'Branco, Prata, Cinza claro',
        'atracao_musical': 'Samba, roda de samba',
        'vista_se': 'Roupas brancas',
        'descricao_gastronomia': (
            'Churrasco, massas, saladas, pudim, pavê, sorvetes e frutas'
        ),
        'manha_tema': 'Paz & Família (Samba e pagode leve)',
        'manha_genero_musical': 'Samba e pagode leve',
        'manha_atividades': 'Momento em família, fotos, abraços, despedida especial',
    },
]


class Command(BaseCommand):
    help = 'Popula noites e manhãs temáticas para cada hotel (idempotente).'

    def handle(self, *args, **options):
        hoteis = Hotel.objects.filter(ativo=True)
        if not hoteis.exists():
            self.stderr.write('Nenhum hotel cadastrado. Rode: python manage.py seed_hoteis')
            return

        total = 0
        for hotel in hoteis:
            for dados in NOITES:
                dia = dados['dia_semana']
                NoiteTematica.objects.update_or_create(
                    hotel=hotel,
                    dia_semana=dia,
                    defaults=dados,
                )
                total += 1

        self.stdout.write(
            self.style.SUCCESS(f'{total} registros de noites temáticas sincronizados.')
        )
