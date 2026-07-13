from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_passeio_pix_beneficiario_passeio_pix_chave'),
    ]

    operations = [
        migrations.AlterField(
            model_name='hotel',
            name='rede_marca',
            field=models.CharField(
                choices=[
                    ('nacional_inn', 'Nacional Inn'),
                    ('euro_suite', 'Euro Suite'),
                    ('dan_inn', 'Dan Inn'),
                    ('cassino_resort', 'Cassino Resort'),
                ],
                default='nacional_inn',
                max_length=20,
                verbose_name='rede / marca',
            ),
        ),
    ]
