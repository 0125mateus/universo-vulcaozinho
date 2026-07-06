from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_fase2_loja_passaporte'),
    ]

    operations = [
        migrations.AddField(
            model_name='hotel',
            name='cor_terciaria',
            field=models.CharField(
                blank=True,
                default='#F7941D',
                max_length=7,
                verbose_name='cor terciária (splash)',
            ),
        ),
    ]
