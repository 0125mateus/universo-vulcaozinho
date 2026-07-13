from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0019_financeiro_operacional'),
    ]

    operations = [
        migrations.AddField(
            model_name='hotel',
            name='whatsapp_setor_pagamentos',
            field=models.CharField(
                blank=True,
                help_text='Número com DDD para enviar planilhas financeiras (ex.: 35999998888).',
                max_length=30,
                verbose_name='WhatsApp setor de pagamentos',
            ),
        ),
    ]
