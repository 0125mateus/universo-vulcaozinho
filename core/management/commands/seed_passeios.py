from django.core.management.base import BaseCommand

from core.models import DiaSemana, Hotel, Passeio

PASSEIOS_PADRAO = [
    (DiaSemana.SEGUNDA, 'City Tour Poços', 'Passeio guiado pelo centro histórico e fontes.'),
    (DiaSemana.TERCA, 'Parque da Cascata', 'Trilha leve e banho de cachoeira.'),
    (DiaSemana.QUARTA, 'Fazenda do Café', 'Degustação e cultura cafeeira da região.'),
    (DiaSemana.QUINTA, 'Morro do São Tomás', 'Teleférico e vista panorâmica da cidade.'),
    (DiaSemana.SEXTA, 'Termas da Colônia', 'Relaxamento nas águas termais.'),
    (DiaSemana.SABADO, 'Vale das Águas', 'Dia de aventura com tirolesa e arvorismo.'),
    (DiaSemana.DOMINGO, 'Passeio Família', 'Programação especial para toda a família.'),
]


class Command(BaseCommand):
    help = 'Cadastra passeios semanais por hotel (idempotente).'

    def handle(self, *args, **options):
        for hotel in Hotel.objects.filter(ativo=True):
            for dia, titulo, descricao in PASSEIOS_PADRAO:
                _, created = Passeio.objects.update_or_create(
                    hotel=hotel,
                    dia_semana=dia,
                    titulo=titulo,
                    defaults={
                        'descricao': descricao,
                        'ordem': dia,
                        'ativo': True,
                    },
                )
                if created:
                    self.stdout.write(f'  + {hotel.slug}: {titulo}')
        self.stdout.write(self.style.SUCCESS('Seed de passeios concluída.'))
