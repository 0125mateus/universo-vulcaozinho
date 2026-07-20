# Generated manually for intelligence layer

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0023_stored_media_file'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConsultaAssistente',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('canal', models.CharField(choices=[('staff', 'Equipe'), ('guest', 'Hóspede')], default='staff', max_length=10)),
                ('mensagem', models.CharField(max_length=500)),
                ('resposta_resumo', models.CharField(blank=True, max_length=800)),
                ('tags', models.CharField(blank=True, help_text='Temas detectados (csv).', max_length=120)),
                ('fonte', models.CharField(default='guided', max_length=20)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('hotel', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='consultas_assistente', to='core.hotel')),
                ('usuario', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='consultas_assistente', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'consulta ao assistente',
                'verbose_name_plural': 'consultas ao assistente',
                'ordering': ['-criado_em'],
            },
        ),
        migrations.AddIndex(
            model_name='consultaassistente',
            index=models.Index(fields=['hotel', 'canal', '-criado_em'], name='core_consul_hotel_c_a0a0f0_idx'),
        ),
    ]
