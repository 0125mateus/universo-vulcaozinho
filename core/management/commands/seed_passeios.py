from django.core.management.base import BaseCommand

from core.models import DiaSemana, Hotel, Passeio

PASSEIOS_PADRAO = [
    (DiaSemana.SEGUNDA, 'City Tour Poços', 'Passeio guiado pelo centro histórico e fontes.', '09:00', '12:00', 'Recepção / Lobby'),
    (DiaSemana.TERCA, 'Parque da Cascata', 'Trilha leve e banho de cachoeira.', '09:30', '13:00', 'Estacionamento'),
    (DiaSemana.QUARTA, 'Fazenda do Café', 'Degustação e cultura cafeeira da região.', '08:30', '12:30', 'Recepção / Lobby'),
    (DiaSemana.QUINTA, 'Morro do São Tomás', 'Teleférico e vista panorâmica da cidade.', '10:00', '13:00', 'Recepção / Lobby'),
    (DiaSemana.SEXTA, 'Termas da Colônia', 'Relaxamento nas águas termais.', '09:00', '12:00', 'Recepção / Lobby'),
    (DiaSemana.SABADO, 'Vale das Águas', 'Dia de aventura com tirolesa e arvorismo.', '08:00', '14:00', 'Estacionamento'),
    (DiaSemana.DOMINGO, 'Passeio Família', 'Programação especial para toda a família.', '10:00', '12:00', 'Recepção / Lobby'),
]


class Command(BaseCommand):
    help = 'Cadastra passeios semanais por hotel (idempotente).'

    def handle(self, *args, **options):
        for hotel in Hotel.objects.filter(ativo=True):
            for dia, titulo, descricao, saida, retorno, ponto in PASSEIOS_PADRAO:
                _, created = Passeio.objects.update_or_create(
                    hotel=hotel,
                    dia_semana=dia,
                    titulo=titulo,
                    defaults={
                        'descricao': descricao,
                        'hora_saida': saida,
                        'hora_retorno': retorno,
                        'ponto_encontro': ponto,
                        'ordem': dia,
                        'ativo': True,
                    },
                )
                if created:
                    self.stdout.write(f'  + {hotel.slug}: {titulo}')
        self.stdout.write(self.style.SUCCESS('Seed de passeios concluída.'))
