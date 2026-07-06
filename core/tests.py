from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

import os

from core.models import (
    FaixaEtaria,
    Hotel,
    Hospede,
    PapelUsuario,
    PerfilUsuario,
    ProdutoLoja,
    calcular_faixa_etaria,
)
from datetime import date


User = get_user_model()


@override_settings(ALLOWED_HOSTS=['testserver'])
class FaixaEtariaTestCase(TestCase):
    def test_bebe(self):
        self.assertEqual(
            calcular_faixa_etaria(date(2025, 1, 1), date(2026, 6, 1)),
            FaixaEtaria.BEBE,
        )

    def test_adulto(self):
        self.assertEqual(
            calcular_faixa_etaria(date(1990, 5, 15), date(2026, 6, 1)),
            FaixaEtaria.ADULTO,
        )

    def test_idoso(self):
        self.assertEqual(
            calcular_faixa_etaria(date(1960, 3, 10), date(2026, 6, 1)),
            FaixaEtaria.IDOSO,
        )


@override_settings(ALLOWED_HOSTS=['testserver'])
class AuthAccessTestCase(TestCase):
    def setUp(self):
        self.hotel = Hotel.objects.create(
            nome='Test Inn', slug='test-inn', ativo=True,
        )
        self.user = User.objects.create_user(username='recep_test', password='testpass123')
        PerfilUsuario.objects.create(
            user=self.user, hotel=self.hotel, papel=PapelUsuario.RECEPCAO, ativo=True,
        )
        self.client = Client()

    def test_recepcao_acessa_modulo(self):
        self.client.login(username='recep_test', password='testpass123')
        session = self.client.session
        session['hotel_slug'] = self.hotel.slug
        session.save()
        resp = self.client.get(reverse('recepcao_index'))
        self.assertEqual(resp.status_code, 200)

    def test_anonimo_redireciona_login(self):
        resp = self.client.get(reverse('recepcao_index'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/entrar/', resp.url)


@override_settings(ALLOWED_HOSTS=['testserver'])
class HospedeValidationTestCase(TestCase):
    def setUp(self):
        self.hotel = Hotel.objects.create(nome='H', slug='h-test', ativo=True)

    def test_checkin_duplicado_bloqueado(self):
        Hospede.objects.create(
            hotel=self.hotel,
            nome_completo='João',
            data_nascimento=date(1990, 1, 1),
            documento='123',
            apartamento='101',
        )
        from django.core.exceptions import ValidationError
        dup = Hospede(
            hotel=self.hotel,
            nome_completo='João 2',
            data_nascimento=date(1991, 1, 1),
            documento='123',
            apartamento='102',
        )
        with self.assertRaises(ValidationError):
            dup.full_clean()


@override_settings(ALLOWED_HOSTS=['testserver'], TELAO_API_KEY='test-key')
class TelaoAPITestCase(TestCase):
    def setUp(self):
        self.hotel = Hotel.objects.create(nome='Telao Hotel', slug='telao-h', ativo=True)

    def test_programacao_atual_sem_key_retorna_403(self):
        url = reverse('telao-programacao-atual', kwargs={'hotel_id': self.hotel.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 403)

    def test_programacao_atual_com_key(self):
        url = reverse('telao-programacao-atual', kwargs={'hotel_id': self.hotel.pk})
        resp = self.client.get(url, HTTP_X_API_KEY='test-key')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('em_andamento', resp.json())


@override_settings(ALLOWED_HOSTS=['testserver'])
class APIHospedeTestCase(TestCase):
    def setUp(self):
        self.hotel = Hotel.objects.create(nome='API Hotel', slug='api-h', ativo=True)
        self.user = User.objects.create_user(username='api_user', password='testpass123')
        PerfilUsuario.objects.create(
            user=self.user, hotel=self.hotel, papel=PapelUsuario.GERENTE, ativo=True,
        )
        self.client = Client()

    def test_lista_hospedes_autenticado(self):
        Hospede.objects.create(
            hotel=self.hotel,
            nome_completo='Maria',
            data_nascimento=date(1985, 6, 15),
            documento='999',
            apartamento='201',
        )
        self.client.login(username='api_user', password='testpass123')
        resp = self.client.get('/api/v1/hospedes/?ativos=1')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreaterEqual(data['count'], 1)


@override_settings(ALLOWED_HOSTS=['testserver'])
class ProdutoLojaTestCase(TestCase):
    def test_gera_codigo_qr_ao_salvar(self):
        p = ProdutoLoja.objects.create(nome='Teste', descricao='x')
        self.assertTrue(p.codigo_qr.startswith('VUL-'))
        self.assertEqual(p.estoque, 0)


class VendaMargemTestCase(TestCase):
    def setUp(self):
        from decimal import Decimal
        self.hotel = Hotel.objects.create(nome='Fin Hotel', slug='fin-h', ativo=True)
        self.produto = ProdutoLoja.objects.create(
            nome='Boné Teste',
            hotel=self.hotel,
            preco=Decimal('40.00'),
            custo=Decimal('20.00'),
            estoque=10,
        )
        self.user = User.objects.create_user(username='loja_test', password='x')

    def test_registrar_venda_calcula_margem(self):
        from decimal import Decimal
        from core.financeiro import registrar_venda_loja
        from core.models import FormaPagamento

        venda = registrar_venda_loja(
            hotel=self.hotel,
            produto=self.produto,
            quantidade=2,
            forma_pagamento=FormaPagamento.PIX,
            registrado_por=self.user,
        )
        self.assertEqual(venda.valor_total, Decimal('80.00'))
        self.assertEqual(venda.custo_total, Decimal('40.00'))
        self.assertEqual(venda.lucro_bruto, Decimal('40.00'))
        self.assertEqual(venda.margem_pct, 50.0)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.estoque, 8)


class ChannelLayerConfigTestCase(TestCase):
    def test_inmemory_sem_redis_url(self):
        from django.conf import settings

        if os.environ.get('REDIS_URL'):
            self.skipTest('REDIS_URL definido no ambiente')
        self.assertEqual(
            settings.CHANNEL_LAYERS['default']['BACKEND'],
            'channels.layers.InMemoryChannelLayer',
        )


@override_settings(
    ALLOWED_HOSTS=['testserver'],
    TELAO_API_KEY='vulcaozinho-telao-dev',
    CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}},
)
class WebSocketRealtimeTestCase(TestCase):
    def setUp(self):
        self.hotel = Hotel.objects.create(nome='WS Hotel', slug='ws-h', ativo=True)

    def test_broadcast_smoke(self):
        from core.realtime import broadcast_hotel_update, hotel_group_name

        self.assertEqual(hotel_group_name(self.hotel.pk), f'hotel_{self.hotel.pk}_live')
        broadcast_hotel_update(self.hotel.pk)

    def test_hospede_save_dispara_broadcast(self):
        from unittest.mock import patch

        with patch('core.signals.broadcast_hotel_update') as mock:
            Hospede.objects.create(
                hotel=self.hotel,
                nome_completo='WS Guest',
                data_nascimento=date(2010, 1, 1),
                documento='ws-1',
                apartamento='101',
            )
            mock.assert_called_with(self.hotel.pk)
