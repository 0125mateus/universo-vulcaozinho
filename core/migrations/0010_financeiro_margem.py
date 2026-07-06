from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_vendaloja'),
    ]

    operations = [
        migrations.AddField(
            model_name='produtoloja',
            name='custo',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0'),
                help_text='Custo de aquisição — usado para calcular margem.',
                max_digits=8,
                verbose_name='custo unitário',
            ),
        ),
        migrations.AddField(
            model_name='vendaloja',
            name='custo_unitario',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='custo unitário'),
        ),
        migrations.AddField(
            model_name='vendaloja',
            name='custo_total',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='custo total'),
        ),
        migrations.AddField(
            model_name='vendaloja',
            name='lucro_bruto',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='lucro bruto'),
        ),
    ]
