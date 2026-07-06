from datetime import time, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import (
    Atividade,
    CategoriaProgramacao,
    Hotel,
    LocalAtividade,
    ProgramacaoDiaria,
    Recreador,
)

# Horários fixos da recreação (infográfico Universo Vulcãozinho)
HORARIOS_FIXOS = [
    ('10:00', 'Início / Boas-vindas'),
    ('13:00', 'Intervalo para Almoço'),
    ('14:00', 'Retorno às Atividades'),
    ('17:00', 'Intervalo / Hora do Lanche'),
    ('17:30', 'Retorno às Atividades'),
    ('21:55', 'Encerramento do Dia'),
]

GRADE_ATIVIDADES = [
    # (inicio, fim, codigo_categoria, nome, icone, frase)
    ('10:00', '10:20', 'vulcao-kids', 'Caça ao Tesouro', '🗺️', 'Em busca do tesouro perdido!'),
    ('10:20', '10:40', 'vulcao-kids', 'Pintura Criativa', '🎨', 'Solte a imaginação!'),
    ('10:40', '11:00', 'vulcao-kids', 'Mini Disco', '🪩', 'Dança e diversão!'),
    ('10:00', '10:20', 'boys-girls', 'Gincana Radical', '🏆', 'Desafios e competição!'),
    ('10:20', '10:40', 'boys-girls', 'Torneio de Vôlei', '🏐', 'Diversão e competição!'),
    ('10:40', '11:00', 'boys-girls', 'Karaokê Teen', '🎤', 'Mostre seu talento!'),
    ('10:00', '10:20', 'adultos', 'Alongamento Matinal', '🧘', 'Bem-estar para começar o dia!'),
    ('10:20', '10:40', 'adultos', 'Beach Tennis', '🎾', 'Diversão e competição!'),
    ('10:40', '11:00', 'adultos', 'Hidroginástica', '💦', 'Exercício na piscina!'),
    ('10:00', '10:20', 'melhor-idade', 'Caminhada Matinal', '🚶', 'Saúde e convivência!'),
    ('10:20', '10:40', 'melhor-idade', 'Jogos de Salão', '🎲', 'Diversão em grupo!'),
    ('10:40', '11:00', 'melhor-idade', 'Bingo da Manhã', '🎯', 'Prêmios e alegria!'),
    ('14:00', '14:20', 'vulcao-kids', 'Hora do Conto', '📖', 'Histórias mágicas!'),
    ('14:20', '14:40', 'vulcao-kids', 'Oficina de Slime', '🧪', 'Mãos à obra!'),
    ('14:00', '14:20', 'boys-girls', 'Desafio Gaming', '🎮', 'Quem leva a melhor?'),
    ('14:20', '14:40', 'boys-girls', 'Dança Teen', '💃', 'Muita energia!'),
    ('14:00', '14:20', 'adultos', 'Vôlei de Praia', '🏐', 'Time contra time!'),
    ('14:20', '14:40', 'adultos', 'Aula de Dança', '💃', 'Aprenda novos passos!'),
    ('14:00', '14:20', 'melhor-idade', 'Tarde da Prosa', '☕', 'Conversa e amizade!'),
    ('14:20', '14:40', 'melhor-idade', 'Música ao Vivo', '🎵', 'Momentos especiais!'),
    ('17:30', '17:50', 'vulcao-kids', 'Jogos na Piscina Kids', '🏊', 'Splash e diversão!'),
    ('17:30', '17:50', 'boys-girls', 'Torneio de Futevôlei', '⚽', 'Disputa acirrada!'),
    ('17:30', '17:50', 'adultos', 'Degustação Temática', '🍷', 'Sabores especiais!'),
    ('17:30', '17:50', 'melhor-idade', 'Bingo Noturno', '🎯', 'Sorteios e prêmios!'),
]

LOCAIS = [
    ('Salão de Recreação', 80),
    ('Piscina Principal', 60),
    ('Piscina Kids', 30),
    ('Quadra de Esportes', 40),
    ('Área Externa', 50),
    ('Salão Melhor Idade', 35),
]


class Command(BaseCommand):
    help = 'Popula programação diária de exemplo por faixa etária (Ages) — idempotente.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dias',
            type=int,
            default=7,
            help='Quantos dias à frente popular (padrão: 7)',
        )

    def handle(self, *args, **options):
        hoteis = Hotel.objects.filter(ativo=True)
        if not hoteis.exists():
            self.stderr.write('Rode primeiro: python manage.py seed_hoteis')
            return

        categorias = {c.codigo: c for c in CategoriaProgramacao.objects.all()}
        if len(categorias) < 4:
            self.stderr.write('Rode primeiro: python manage.py seed_categorias')
            return

        dias = options['dias']
        hoje = timezone.localdate()
        total = 0

        for hotel in hoteis:
            locais = {}
            for nome, cap in LOCAIS:
                local, _ = LocalAtividade.objects.update_or_create(
                    hotel=hotel,
                    nome=nome,
                    defaults={'capacidade_maxima': cap, 'ativo': True},
                )
                locais[nome] = local

            recreador, _ = Recreador.objects.update_or_create(
                hotel=hotel,
                nome='Equipe Recreação',
                defaults={'ativo': True},
            )

            local_map = {
                'vulcao-kids': locais['Piscina Kids'],
                'boys-girls': locais['Quadra de Esportes'],
                'adultos': locais['Piscina Principal'],
                'melhor-idade': locais['Salão Melhor Idade'],
            }

            for dia_offset in range(dias):
                data = hoje + timedelta(days=dia_offset)
                for hi, hf, codigo, nome, icone, frase in GRADE_ATIVIDADES:
                    cat = categorias[codigo]
                    local = local_map.get(codigo, locais['Salão de Recreação'])

                    atividade, _ = Atividade.objects.update_or_create(
                        hotel=hotel,
                        nome=nome,
                        defaults={
                            'descricao': frase,
                            'frase_chamada': frase,
                            'icone': icone,
                            'categoria': cat,
                            'local_padrao': local,
                            'duracao_minutos': 20,
                            'ativo': True,
                        },
                    )

                    hora_i = time(int(hi[:2]), int(hi[3:5]))
                    hora_f = time(int(hf[:2]), int(hf[3:5]))

                    _, created = ProgramacaoDiaria.objects.update_or_create(
                        hotel=hotel,
                        data=data,
                        hora_inicio=hora_i,
                        local=local,
                        defaults={
                            'hora_fim': hora_f,
                            'atividade': atividade,
                            'categoria': cat,
                            'recreador': recreador,
                            'vagas_total': local.capacidade_maxima,
                        },
                    )
                    if created:
                        total += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Programação sincronizada para {hoteis.count()} hotel(is), '
                f'{dias} dia(s). Novos registros: {total}.'
            )
        )
