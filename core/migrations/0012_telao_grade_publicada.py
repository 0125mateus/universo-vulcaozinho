# Generated manually for TelaoGradePublicada

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0011_importacao_eventos'),
    ]

    operations = [
        migrations.CreateModel(
            name='TelaoGradePublicada',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data', models.DateField(verbose_name='data da grade')),
                ('total_atividades', models.PositiveIntegerField(default=0, verbose_name='total de atividades')),
                ('ativo', models.BooleanField(default=True, verbose_name='ativa no telão')),
                ('publicado_em', models.DateTimeField(auto_now=True, verbose_name='publicado em')),
                ('hotel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='grades_telao', to='core.hotel', verbose_name='hotel')),
                ('publicado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='grades_telao_publicadas', to=settings.AUTH_USER_MODEL, verbose_name='publicado por')),
            ],
            options={
                'verbose_name': 'grade publicada no telão',
                'verbose_name_plural': 'grades publicadas no telão',
                'ordering': ['-publicado_em'],
                'unique_together': {('hotel', 'data')},
            },
        ),
    ]
