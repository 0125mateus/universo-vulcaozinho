from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0008_hotel_cor_terciaria'),
    ]

    operations = [
        migrations.CreateModel(
            name='VendaLoja',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descricao', models.CharField(max_length=160, verbose_name='descrição')),
                ('quantidade', models.PositiveIntegerField(default=1, verbose_name='quantidade')),
                ('valor_unitario', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='valor unitário')),
                ('valor_total', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='valor total')),
                ('forma_pagamento', models.CharField(
                    choices=[
                        ('dinheiro', 'Dinheiro'),
                        ('cartao', 'Cartão'),
                        ('pix', 'PIX'),
                        ('hospede', 'Conta hóspede'),
                    ],
                    default='pix',
                    max_length=20,
                    verbose_name='forma de pagamento',
                )),
                ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='data da venda')),
                ('hotel', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='vendas_loja',
                    to='core.hotel',
                    verbose_name='hotel',
                )),
                ('produto', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='vendas',
                    to='core.produtoloja',
                    verbose_name='produto',
                )),
                ('registrado_por', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='vendas_loja_registradas',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='registrado por',
                )),
            ],
            options={
                'verbose_name': 'venda da loja',
                'verbose_name_plural': 'vendas da loja',
                'ordering': ['-criado_em'],
            },
        ),
    ]
