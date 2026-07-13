import decimal

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0018_alter_hotel_rede_marca_cassino_resort'),
    ]

    operations = [
        migrations.CreateModel(
            name='PeriodoOperacional',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('extras_recreadores', 'Extras de recreadores'), ('atracoes', 'Atrações / artistas'), ('compras', 'Compras semanais')], max_length=30, verbose_name='tipo')),
                ('titulo', models.CharField(max_length=120, verbose_name='título')),
                ('data_inicio', models.DateField(verbose_name='data início')),
                ('data_fim', models.DateField(verbose_name='data fim')),
                ('ocupacao_pct', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True, verbose_name='ocupação %')),
                ('qtd_pax', models.PositiveIntegerField(blank=True, null=True, verbose_name='qtd. hóspedes')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('criado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='periodos_operacionais_criados', to=settings.AUTH_USER_MODEL)),
                ('hotel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='periodos_operacionais', to='core.hotel', verbose_name='hotel')),
            ],
            options={
                'verbose_name': 'período operacional',
                'verbose_name_plural': 'períodos operacionais',
                'ordering': ['-data_inicio', 'titulo'],
            },
        ),
        migrations.CreateModel(
            name='PagamentoAtracao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_label', models.CharField(blank=True, max_length=80, verbose_name='dia / referência')),
                ('data_evento', models.DateField(blank=True, null=True, verbose_name='data do evento')),
                ('artista', models.CharField(max_length=200, verbose_name='artista / prestador')),
                ('atracao', models.CharField(blank=True, max_length=200, verbose_name='atração / tipo')),
                ('valor', models.DecimalField(decimal_places=2, default=decimal.Decimal('0'), max_digits=10, verbose_name='valor (R$)')),
                ('chave_pix', models.CharField(blank=True, max_length=200, verbose_name='chave PIX')),
                ('evento', models.CharField(blank=True, max_length=200, verbose_name='evento')),
                ('pacote', models.CharField(blank=True, max_length=120, verbose_name='pacote')),
                ('tipo_servico', models.CharField(blank=True, max_length=120, verbose_name='tipo de serviço')),
                ('responsavel', models.CharField(blank=True, max_length=120, verbose_name='responsável')),
                ('horario', models.CharField(blank=True, max_length=40, verbose_name='horário')),
                ('local_dept', models.CharField(blank=True, max_length=120, verbose_name='local / dept.')),
                ('status', models.CharField(choices=[('pendente', 'Pendente'), ('autorizado', 'Autorizado'), ('pago', 'Pago'), ('cancelado', 'Cancelado')], default='pendente', max_length=20, verbose_name='status')),
                ('autorizacao_diretoria', models.CharField(blank=True, max_length=80, verbose_name='autorização diretoria')),
                ('observacoes', models.TextField(blank=True, verbose_name='observações')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('hotel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pagamentos_atracoes', to='core.hotel')),
                ('periodo', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pagamentos', to='core.periodooperacional')),
            ],
            options={
                'verbose_name': 'pagamento de atração',
                'verbose_name_plural': 'pagamentos de atrações',
                'ordering': ['data_evento', 'artista'],
            },
        ),
        migrations.CreateModel(
            name='ItemCompraSemanal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descricao', models.CharField(max_length=300, verbose_name='material / item')),
                ('quantidade', models.PositiveIntegerField(default=1, verbose_name='quantidade')),
                ('link_fornecedor', models.CharField(blank=True, max_length=500, verbose_name='link fornecedor')),
                ('preco_unitario', models.DecimalField(decimal_places=2, default=decimal.Decimal('0'), max_digits=10, verbose_name='preço unitário')),
                ('ordem', models.PositiveSmallIntegerField(default=0)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('hotel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='compras_semanais', to='core.hotel')),
                ('periodo', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='itens_compra', to='core.periodooperacional')),
            ],
            options={
                'verbose_name': 'item de compra',
                'verbose_name_plural': 'itens de compra',
                'ordering': ['ordem', 'descricao'],
            },
        ),
        migrations.CreateModel(
            name='ExtraRecreador',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=120, verbose_name='recreador')),
                ('valor_seg', models.DecimalField(decimal_places=2, default=decimal.Decimal('0'), max_digits=8)),
                ('valor_ter', models.DecimalField(decimal_places=2, default=decimal.Decimal('0'), max_digits=8)),
                ('valor_qua', models.DecimalField(decimal_places=2, default=decimal.Decimal('0'), max_digits=8)),
                ('valor_qui', models.DecimalField(decimal_places=2, default=decimal.Decimal('0'), max_digits=8)),
                ('valor_sex', models.DecimalField(decimal_places=2, default=decimal.Decimal('0'), max_digits=8)),
                ('valor_sab', models.DecimalField(decimal_places=2, default=decimal.Decimal('0'), max_digits=8)),
                ('valor_dom', models.DecimalField(decimal_places=2, default=decimal.Decimal('0'), max_digits=8)),
                ('ordem', models.PositiveSmallIntegerField(default=0)),
                ('hotel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='extras_recreadores', to='core.hotel')),
                ('periodo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='extras_recreadores', to='core.periodooperacional')),
            ],
            options={
                'verbose_name': 'extra de recreador',
                'verbose_name_plural': 'extras de recreadores',
                'ordering': ['ordem', 'nome'],
            },
        ),
    ]
