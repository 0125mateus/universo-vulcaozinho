from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

import json
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
from datetime import date, time


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

    def test_checkin_form_sem_hotel_id_nao_estoura(self):
        from core.forms import HospedeForm

        form = HospedeForm(
            data={
                'nome_completo': 'Maria',
                'data_nascimento': '1990-05-10',
                'documento': '999',
                'apartamento': '201',
                'data_checkin': '2026-07-06',
                'data_checkout': '',
                'observacoes': '',
            },
            hotel=self.hotel,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_menor_idade_exige_responsavel(self):
        from core.forms import HospedeForm

        form = HospedeForm(
            data={
                'nome_completo': 'Criança Teste',
                'data_nascimento': '2015-05-10',
                'documento': '888',
                'apartamento': '202',
                'data_checkin': '2026-07-06',
                'data_checkout': '',
                'observacoes': '',
            },
            hotel=self.hotel,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('responsavel_nome', form.errors)
        self.assertIn('responsavel_assinatura', form.errors)

    def test_menor_idade_com_responsavel_valido(self):
        from core.forms import HospedeForm

        assinatura = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAAB'
        form = HospedeForm(
            data={
                'nome_completo': 'Criança Teste',
                'data_nascimento': '2015-05-10',
                'documento': '777',
                'apartamento': '203',
                'data_checkin': '2026-07-06',
                'data_checkout': '',
                'observacoes': '',
                'responsavel_nome': 'Fulana Responsável',
                'responsavel_documento': '123.456.789-00',
                'responsavel_parentesco': 'mae',
                'responsavel_telefone': '(11) 99999-0000',
                'responsavel_assinatura': assinatura,
            },
            hotel=self.hotel,
        )
        self.assertTrue(form.is_valid(), form.errors)
        hospede = form.save()
        self.assertTrue(hospede.is_menor_idade)
        self.assertEqual(hospede.responsavel_nome, 'Fulana Responsável')
        self.assertTrue(hospede.responsavel_assinatura)
        self.assertIsNotNone(hospede.responsavel_assinado_em)

    def test_checkin_post_via_view(self):
        from core.management.commands.seed_categorias import CATEGORIAS
        from core.models import CategoriaProgramacao, PapelUsuario, PerfilUsuario

        user = User.objects.create_user('rec_checkin', password='testpass123')
        PerfilUsuario.objects.create(
            user=user,
            papel=PapelUsuario.RECEPCAO,
            hotel=self.hotel,
            ativo=True,
        )
        for dados in CATEGORIAS:
            d = dict(dados)
            codigo = d.pop('codigo')
            CategoriaProgramacao.objects.update_or_create(codigo=codigo, defaults=d)

        self.client.login(username='rec_checkin', password='testpass123')
        session = self.client.session
        session['hotel_slug'] = self.hotel.slug
        session.save()

        resp = self.client.post(reverse('recepcao_checkin'), {
            'nome_completo': 'Visitante Teste',
            'data_nascimento': '1990-03-15',
            'documento': 'DOC-001',
            'apartamento': '305',
            'data_checkin': '2026-07-06',
            'data_checkout': '',
            'observacoes': '',
        })
        self.assertEqual(resp.status_code, 302, resp.content)
        h = Hospede.objects.filter(hotel=self.hotel, apartamento='305').first()
        self.assertIsNotNone(h)
        self.assertEqual(h.documento, 'DOC001')

    def test_formatar_cpf(self):
        from core.documento_utils import formatar_documento, normalizar_documento

        self.assertEqual(formatar_documento('11186955694'), '111.869.556-94')
        self.assertEqual(normalizar_documento('111.869.556-94'), '11186955694')

    def test_duplicado_ignora_mascara(self):
        from core.documento_utils import documento_duplicado_ativo

        Hospede.objects.create(
            hotel=self.hotel,
            nome_completo='Ana',
            data_nascimento=date(1985, 6, 1),
            documento='111.869.556-94',
            apartamento='101',
        )
        self.assertTrue(documento_duplicado_ativo(self.hotel, '11186955694'))

    def test_checkin_salva_cpf_formatado(self):
        from core.models import PapelUsuario, PerfilUsuario

        user = User.objects.create_user('rec_doc', password='testpass123')
        PerfilUsuario.objects.create(
            user=user,
            papel=PapelUsuario.RECEPCAO,
            hotel=self.hotel,
            ativo=True,
        )
        self.client.login(username='rec_doc', password='testpass123')
        session = self.client.session
        session['hotel_slug'] = self.hotel.slug
        session.save()

        self.client.post(reverse('recepcao_checkin'), {
            'nome_completo': 'CPF Teste',
            'data_nascimento': '1990-01-01',
            'documento': '11186955694',
            'apartamento': '401',
            'data_checkin': '2026-07-06',
            'data_checkout': '',
            'observacoes': '',
        })
        h = Hospede.objects.get(hotel=self.hotel, apartamento='401')
        self.assertEqual(h.documento, '111.869.556-94')

    def test_excluir_hospede_via_view(self):
        from core.models import PapelUsuario, PerfilUsuario

        h = Hospede.objects.create(
            hotel=self.hotel,
            nome_completo='Para Excluir',
            data_nascimento=date(2000, 1, 1),
            documento='777.888.999-00',
            apartamento='999',
        )
        user = User.objects.create_user('rec_del', password='testpass123')
        PerfilUsuario.objects.create(
            user=user,
            papel=PapelUsuario.RECEPCAO,
            hotel=self.hotel,
            ativo=True,
        )
        self.client.login(username='rec_del', password='testpass123')
        session = self.client.session
        session['hotel_slug'] = self.hotel.slug
        session.save()

        resp = self.client.post(reverse('recepcao_hospede_excluir', kwargs={'pk': h.pk}))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Hospede.objects.filter(pk=h.pk).exists())

    def test_termo_responsabilidade_menor(self):
        from core.models import PapelUsuario, PerfilUsuario

        h = Hospede.objects.create(
            hotel=self.hotel,
            nome_completo='Menor Termo',
            data_nascimento=date(2015, 1, 1),
            documento='111.222.333-44',
            apartamento='888',
            responsavel_nome='Responsável Termo',
            responsavel_documento='555.666.777-88',
            responsavel_parentesco='mae',
        )
        user = User.objects.create_user('rec_termo', password='testpass123')
        PerfilUsuario.objects.create(
            user=user,
            papel=PapelUsuario.RECEPCAO,
            hotel=self.hotel,
            ativo=True,
        )
        self.client.login(username='rec_termo', password='testpass123')
        session = self.client.session
        session['hotel_slug'] = self.hotel.slug
        session.save()

        resp = self.client.get(reverse('recepcao_hospede_termo', kwargs={'pk': h.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Termo de Responsabilidade')
        self.assertContains(resp, 'Responsável Termo')

    def test_termo_whatsapp_e_link_publico(self):
        from core.models import PapelUsuario, PerfilUsuario
        from core.termo_utils import assinar_token_termo

        h = Hospede.objects.create(
            hotel=self.hotel,
            nome_completo='Menor WhatsApp',
            data_nascimento=date(2015, 1, 1),
            documento='111.222.333-44',
            apartamento='888',
            responsavel_nome='Marcos',
            responsavel_documento='555.666.777-88',
            responsavel_parentesco='pai',
            responsavel_telefone='31990666323',
        )
        user = User.objects.create_user('rec_termo_wa', password='testpass123')
        PerfilUsuario.objects.create(
            user=user,
            papel=PapelUsuario.RECEPCAO,
            hotel=self.hotel,
            ativo=True,
        )
        self.client.login(username='rec_termo_wa', password='testpass123')
        session = self.client.session
        session['hotel_slug'] = self.hotel.slug
        session.save()

        resp = self.client.get(reverse('recepcao_hospede_detalhe', kwargs={'pk': h.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Enviar termo no WhatsApp')
        self.assertContains(resp, 'wa.me/5531990666323')

        token = assinar_token_termo(h.pk)
        self.client.logout()
        resp_pub = self.client.get(reverse('termo_publico', kwargs={'token': token}))
        self.assertEqual(resp_pub.status_code, 200)
        self.assertContains(resp_pub, 'Menor WhatsApp')

    def test_hospede_inexistente_redireciona_lista(self):
        from core.models import PapelUsuario, PerfilUsuario

        user = User.objects.create_user('rec_404', password='testpass123')
        PerfilUsuario.objects.create(
            user=user,
            papel=PapelUsuario.RECEPCAO,
            hotel=self.hotel,
            ativo=True,
        )
        self.client.login(username='rec_404', password='testpass123')
        session = self.client.session
        session['hotel_slug'] = self.hotel.slug
        session.save()

        resp = self.client.get(reverse('recepcao_hospede_detalhe', kwargs={'pk': 99999}))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('recepcao_hospedes'))


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
        data = resp.json()
        self.assertIn('em_andamento', data)
        self.assertIn('status', data)

    def test_grade_telao_sem_publicar_nao_retorna_colunas(self):
        from datetime import time as dt_time
        from core.models import Atividade, CategoriaProgramacao, LocalAtividade, ProgramacaoDiaria
        from django.utils import timezone

        cat = CategoriaProgramacao.objects.create(
            codigo='kids-g', nome='Kids', idade_min=7, idade_max=12, ordem=1, cor='#FF0000',
        )
        local = LocalAtividade.objects.create(hotel=self.hotel, nome='Salão')
        ativ = Atividade.objects.create(
            hotel=self.hotel, nome='Gincana', categoria=cat, local_padrao=local,
        )
        hoje = timezone.localdate()
        ProgramacaoDiaria.objects.create(
            hotel=self.hotel, data=hoje,
            hora_inicio=dt_time(10, 0), hora_fim=dt_time(11, 0),
            atividade=ativ, local=local, categoria=cat, vagas_total=20,
        )
        url = reverse('telao-grade-publicada', kwargs={'hotel_id': self.hotel.pk})
        resp = self.client.get(url, HTTP_X_API_KEY='test-key')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data['publicada'])
        self.assertEqual(data['total'], 0)
        self.assertEqual(data['total_disponivel'], 1)
        self.assertEqual(data['colunas'], [])

    def test_grade_telao_publicada_retorna_colunas(self):
        from datetime import time as dt_time
        from core.models import Atividade, CategoriaProgramacao, LocalAtividade, ProgramacaoDiaria, TelaoGradePublicada
        from django.utils import timezone

        cat = CategoriaProgramacao.objects.create(
            codigo='kids-pub', nome='Kids', idade_min=7, idade_max=12, ordem=1, cor='#FF0000',
        )
        local = LocalAtividade.objects.create(hotel=self.hotel, nome='Salão')
        ativ = Atividade.objects.create(
            hotel=self.hotel, nome='Gincana', categoria=cat, local_padrao=local,
        )
        hoje = timezone.localdate()
        ProgramacaoDiaria.objects.create(
            hotel=self.hotel, data=hoje,
            hora_inicio=dt_time(10, 0), hora_fim=dt_time(11, 0),
            atividade=ativ, local=local, categoria=cat, vagas_total=20,
        )
        TelaoGradePublicada.objects.create(
            hotel=self.hotel, data=hoje, total_atividades=1, ativo=True,
        )
        url = reverse('telao-grade-publicada', kwargs={'hotel_id': self.hotel.pk})
        resp = self.client.get(url, HTTP_X_API_KEY='test-key')
        data = resp.json()
        self.assertTrue(data['publicada'])
        self.assertEqual(data['total'], 1)
        kids = next(c for c in data['colunas'] if c['faixa'] == 'Kids')
        self.assertEqual(kids['atividades'][0]['nome'], 'Gincana')

    def test_programacao_apos_horario_mostra_amanha(self):
        from datetime import time as dt_time
        from core.models import Atividade, CategoriaProgramacao, LocalAtividade, ProgramacaoDiaria
        from core.views_telao_api import resolver_programacao_telao
        from django.utils import timezone

        cat = CategoriaProgramacao.objects.create(
            codigo='adultos-t', nome='Adultos', idade_min=18, idade_max=99, ordem=1,
        )
        local = LocalAtividade.objects.create(hotel=self.hotel, nome='Piscina')
        ativ = Atividade.objects.create(
            hotel=self.hotel, nome='Alongamento', categoria=cat, local_padrao=local,
        )
        hoje = timezone.localdate()
        ProgramacaoDiaria.objects.create(
            hotel=self.hotel,
            data=hoje,
            hora_inicio=dt_time(10, 0),
            hora_fim=dt_time(11, 0),
            atividade=ativ,
            local=local,
            categoria=cat,
            vagas_total=30,
        )
        from datetime import timedelta
        amanha = hoje + timedelta(days=1)
        ProgramacaoDiaria.objects.create(
            hotel=self.hotel,
            data=amanha,
            hora_inicio=dt_time(10, 0),
            hora_fim=dt_time(11, 0),
            atividade=ativ,
            local=local,
            categoria=cat,
            vagas_total=30,
        )

        res = resolver_programacao_telao(
            self.hotel.pk,
            hoje=hoje,
            agora=dt_time(19, 0),
        )
        self.assertEqual(res['status'], 'amanha')
        self.assertEqual(res['destaque'].atividade.nome, 'Alongamento')

    def test_publicar_grade_no_telao(self):
        from datetime import time as dt_time
        from core.models import Atividade, CategoriaProgramacao, LocalAtividade, ProgramacaoDiaria, TelaoGradePublicada
        from core.views_programacao import publicar_grade_no_telao

        cat = CategoriaProgramacao.objects.create(
            codigo='kids-t', nome='Kids', idade_min=7, idade_max=12, ordem=1, cor='#FF0000',
        )
        local = LocalAtividade.objects.create(hotel=self.hotel, nome='Salão')
        ativ = Atividade.objects.create(
            hotel=self.hotel, nome='Gincana', categoria=cat, local_padrao=local,
        )
        hoje = timezone.localdate()
        ProgramacaoDiaria.objects.create(
            hotel=self.hotel, data=hoje,
            hora_inicio=dt_time(10, 0), hora_fim=dt_time(11, 0),
            atividade=ativ, local=local, categoria=cat, vagas_total=20,
        )
        user = User.objects.create_user('pub_telao', password='x')
        ok, msg = publicar_grade_no_telao(self.hotel, user)
        self.assertTrue(ok)
        self.assertTrue(TelaoGradePublicada.objects.filter(hotel=self.hotel, data=hoje, ativo=True).exists())


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


class ImportacaoXlsxTestCase(TestCase):
    def setUp(self):
        from io import BytesIO
        import openpyxl
        from core.management.commands.seed_categorias import CATEGORIAS
        from core.models import CategoriaProgramacao

        self.hotel = Hotel.objects.create(nome='Imp Hotel', slug='imp-h', ativo=True)
        for dados in CATEGORIAS:
            d = dict(dados)
            codigo = d.pop('codigo')
            CategoriaProgramacao.objects.update_or_create(codigo=codigo, defaults=d)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Adultos Teste'
        ws.append(['Data', 'Dia da Semana', 'Hora', 'Atividade', 'Local', 'Responsável'])
        ws.append([timezone.localdate(), 'Terça', time(10, 0), 'Alongamento', 'Local: Solarium', 'Recreação'])
        buf = BytesIO()
        wb.save(buf)
        buf.seek(0)
        self.buf_prog = buf

        wb2 = openpyxl.Workbook()
        ws2 = wb2.active
        ws2.title = '03-2026'
        for _ in range(5):
            ws2.append([])
        ws2.append(['PACOTE', 'MÊS', 'EVENTO', 'DESCRIÇÃO', 'TIPO SERVIÇO / FORNECEDOR', 'RESPONSÁVEL', 'DIA', 'DATA INICIAL'])
        ws2.append(['', 'MARÇO', 'BINGO MUSICAL', 'Bingo com música', 'MÚSICO', 'Kamila', 'SÁBADO', date(2026, 3, 14)])
        buf2 = BytesIO()
        wb2.save(buf2)
        buf2.seek(0)
        self.buf_eventos = buf2

    def test_importar_programacao(self):
        from core.importacao_xlsx import importar_programacao
        from core.models import ProgramacaoDiaria

        r = importar_programacao(self.hotel, self.buf_prog)
        self.assertEqual(r.criados, 1)
        self.assertTrue(ProgramacaoDiaria.objects.filter(hotel=self.hotel).exists())

    def test_importar_eventos(self):
        from core.importacao_xlsx import importar_eventos
        from core.models import EventoRecreacao

        r = importar_eventos(self.hotel, self.buf_eventos)
        self.assertEqual(r.criados, 1)
        ev = EventoRecreacao.objects.get(hotel=self.hotel)
        self.assertEqual(ev.nome, 'BINGO MUSICAL')
        self.assertEqual(ev.prestador, '')

    def test_cruzar_planilha(self):
        from core.analise_faixas import cruzar_planilha

        r = cruzar_planilha(self.buf_prog)
        self.assertGreater(r.total_linhas, 0)
        self.assertTrue(r.faixas)

    def test_cruzar_banco(self):
        from core.analise_faixas import cruzar_banco
        from core.importacao_xlsx import importar_programacao

        importar_programacao(self.hotel, self.buf_prog)
        r = cruzar_banco(self.hotel, dias=90)
        self.assertGreater(r.total_linhas, 0)


class AnaliseFaixasUnitTestCase(TestCase):
    def test_cruzamento_exclusividade_e_matriz(self):
        from core.analise_faixas import _calcular_cruzamento
        from core.importacao_xlsx import LinhaProgramacao

        linhas = [
            LinhaProgramacao('Kids', 'Kids 7-12', 'vulcao-kids', date(2026, 3, 1), time(10, 0), 'Pintura', 'Sala Kids'),
            LinhaProgramacao('Kids', 'Kids 7-12', 'vulcao-kids', date(2026, 3, 1), time(11, 0), 'Pintura', 'Sala Kids'),
            LinhaProgramacao('Kids', 'Kids 7-12', 'vulcao-kids', date(2026, 3, 1), time(14, 0), 'Caça ao Tesouro', 'Jardim'),
            LinhaProgramacao('Adultos', 'Adultos', 'adultos', date(2026, 3, 1), time(10, 0), 'Alongamento', 'Piscina'),
            LinhaProgramacao('Adultos', 'Adultos', 'adultos', date(2026, 3, 1), time(11, 0), 'Alongamento', 'Piscina'),
            LinhaProgramacao('Adultos', 'Adultos', 'adultos', date(2026, 3, 1), time(15, 0), 'Bingo', 'Salão'),
            LinhaProgramacao('Kids', 'Kids 7-12', 'vulcao-kids', date(2026, 3, 2), time(10, 0), 'Bingo', 'Salão'),
            LinhaProgramacao('Teens', 'Teens 13-17', 'boys-girls', date(2026, 3, 2), time(11, 0), 'Bingo', 'Salão'),
        ]
        r = _calcular_cruzamento(linhas, fonte='teste')
        self.assertEqual(r.total_linhas, 8)
        self.assertEqual(len(r.faixas), 3)

        kids = next(f for f in r.faixas if f.label == 'Kids 7-12')
        self.assertEqual(kids.top_atividades[0].nome, 'Pintura')
        self.assertEqual(kids.top_atividades[0].exclusividade_pct, 100.0)
        self.assertTrue(any(m['nome'] == 'Bingo' for m in r.multifaixa))
        self.assertEqual(r.matriz[0]['rank'], 1)
        self.assertEqual(len(r.matriz[0]['cells']), 3)


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


@override_settings(ALLOWED_HOSTS=['testserver'])
class ProgramacaoGestaoTestCase(TestCase):
    def setUp(self):
        from core.models import Atividade, CategoriaProgramacao, LocalAtividade, ProgramacaoDiaria

        self.ProgramacaoDiaria = ProgramacaoDiaria
        self.hotel = Hotel.objects.create(nome='Prog Hotel', slug='prog-h', ativo=True)
        self.cat = CategoriaProgramacao.objects.create(
            codigo='kids-p', nome='Kids', idade_min=7, idade_max=12, ordem=1,
        )
        self.local = LocalAtividade.objects.create(hotel=self.hotel, nome='Salão')
        self.ativ = Atividade.objects.create(
            hotel=self.hotel, nome='Gincana', categoria=self.cat, local_padrao=self.local,
        )
        self.user = User.objects.create_user('prog_user', password='testpass123')
        PerfilUsuario.objects.create(
            user=self.user,
            papel=PapelUsuario.RECEPCAO,
            hotel=self.hotel,
            ativo=True,
        )
        self.hoje = timezone.localdate()
        self.prog = ProgramacaoDiaria.objects.create(
            hotel=self.hotel,
            data=self.hoje,
            hora_inicio=time(10, 0),
            hora_fim=time(11, 0),
            atividade=self.ativ,
            local=self.local,
            categoria=self.cat,
            vagas_total=25,
        )
        self.client = Client()
        self.client.login(username='prog_user', password='testpass123')
        session = self.client.session
        session['hotel_slug'] = self.hotel.slug
        session.save()

    def test_gestao_list_requer_login(self):
        self.client.logout()
        resp = self.client.get(reverse('programacao_gestao'))
        self.assertEqual(resp.status_code, 302)

    def test_gestao_list_autenticado(self):
        resp = self.client.get(reverse('programacao_gestao'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Gincana')

    def test_editar_programacao(self):
        url = reverse('programacao_editar', kwargs={'pk': self.prog.pk})
        resp = self.client.post(url, {
            'data': self.hoje.isoformat(),
            'hora_inicio': '10:30',
            'hora_fim': '11:30',
            'atividade': self.ativ.pk,
            'local': self.local.pk,
            'categoria': self.cat.pk,
            'recreador': '',
            'vagas_total': 30,
            'observacoes': '',
        })
        self.assertEqual(resp.status_code, 302)
        self.prog.refresh_from_db()
        self.assertEqual(self.prog.hora_inicio, time(10, 30))
        self.assertEqual(self.prog.vagas_total, 30)

    def test_excluir_programacao(self):
        url = reverse('programacao_excluir', kwargs={'pk': self.prog.pk})
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(self.ProgramacaoDiaria.objects.filter(pk=self.prog.pk).exists())

    def test_excluir_lote(self):
        prog2 = self.ProgramacaoDiaria.objects.create(
            hotel=self.hotel,
            data=self.hoje,
            hora_inicio=time(14, 0),
            hora_fim=time(15, 0),
            atividade=self.ativ,
            local=self.local,
            categoria=self.cat,
            vagas_total=25,
        )
        resp = self.client.post(reverse('programacao_acao_lote'), {
            'action': 'delete',
            'data': self.hoje.isoformat(),
            'ids': [self.prog.pk, prog2.pk],
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(self.ProgramacaoDiaria.objects.filter(hotel=self.hotel, data=self.hoje).count(), 0)

    def test_criar_varias_atividades(self):
        from core.models import Atividade

        ativ2 = Atividade.objects.create(
            hotel=self.hotel, nome='Pintura', categoria=self.cat, local_padrao=self.local,
        )
        resp = self.client.post(reverse('programacao_novas'), {
            'data': self.hoje.isoformat(),
            'hora_inicio': '14:00',
            'duracao_minutos': 50,
            'local': self.local.pk,
            'categoria': self.cat.pk,
            'recreador': '',
            'vagas_total': 30,
            'atividades': [self.ativ.pk, ativ2.pk],
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            self.ProgramacaoDiaria.objects.filter(hotel=self.hotel, data=self.hoje).count(),
            3,
        )


@override_settings(ALLOWED_HOSTS=['testserver'])
class HospedeAppTestCase(TestCase):
    def setUp(self):
        from core.models import Atividade, CategoriaProgramacao, LocalAtividade, PassaporteHospede, ProgramacaoDiaria

        self.hotel = Hotel.objects.create(nome='App Hotel', slug='dan-inn', ativo=True)
        self.cat = CategoriaProgramacao.objects.create(
            codigo='kids-app', nome='Vulcão Kids', idade_min=7, idade_max=12, ordem=1, cor='#E67E22',
        )
        self.local = LocalAtividade.objects.create(hotel=self.hotel, nome='Piscina Kids')
        self.ativ = Atividade.objects.create(
            hotel=self.hotel, nome='Gincana', categoria=self.cat, local_padrao=self.local,
        )
        self.hospede = Hospede.objects.create(
            hotel=self.hotel,
            nome_completo='Maria Silva',
            data_nascimento=date(2015, 3, 10),
            documento='529.982.247-25',
            apartamento='302',
        )
        PassaporteHospede.objects.create(hospede=self.hospede, moedas=15)
        self.hoje = timezone.localdate()
        ProgramacaoDiaria.objects.create(
            hotel=self.hotel, data=self.hoje,
            hora_inicio=time(10, 0), hora_fim=time(11, 0),
            atividade=self.ativ, local=self.local, categoria=self.cat, vagas_total=20,
        )
        self.client = Client()
        session = self.client.session
        session['hotel_slug'] = self.hotel.slug
        session.save()

    def test_login_hospede(self):
        resp = self.client.post(reverse('hospede_app_login'), {
            'apartamento': '302',
            'documento': '24725',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(self.client.session.get('hospede_app_id'), self.hospede.pk)
        self.assertEqual(self.client.session.get('hotel_slug'), self.hotel.slug)

    def test_login_sem_hotel_na_sessao(self):
        session = self.client.session
        session.pop('hotel_slug', None)
        session.save()
        resp = self.client.post(reverse('hospede_app_login'), {
            'apartamento': '302',
            'documento': '24725',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(self.client.session.get('hospede_app_id'), self.hospede.pk)

    def test_identificar_hotel_api(self):
        resp = self.client.get(reverse('hospede_app_identificar_hotel'), {
            'apartamento': '302',
            'documento': '24725',
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['hotel_slug'], self.hotel.slug)
        self.assertEqual(data['primeiro_nome'], 'Maria')

    def test_login_invalido(self):
        resp = self.client.post(reverse('hospede_app_login'), {
            'apartamento': '999',
            'documento': '0000',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn('hospede_app_id', self.client.session)

    def test_home_requer_login(self):
        resp = self.client.get(reverse('hospede_app_home'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/app/entrar/', resp.url)

    def test_home_autenticado(self):
        self.client.post(reverse('hospede_app_login'), {
            'apartamento': '302',
            'documento': '24725',
        })
        resp = self.client.get(reverse('hospede_app_home'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Maria')
        self.assertContains(resp, 'Vulcão Kids')

    def test_programacao_filtra_faixa(self):
        self.client.post(reverse('hospede_app_login'), {
            'apartamento': '302',
            'documento': '24725',
        })
        resp = self.client.get(reverse('hospede_app_programacao'))
        self.assertContains(resp, 'Gincana')
        self.assertContains(resp, 'sua faixa')

    def test_manifest_pwa(self):
        resp = self.client.get(reverse('hospede_app_manifest'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('application/manifest+json', resp['Content-Type'])


@override_settings(ALLOWED_HOSTS=['testserver'])
class PasseiosTestCase(TestCase):
    def setUp(self):
        from core.models import Passeio

        self.hotel = Hotel.objects.create(nome='Passeio Hotel', slug='dan-inn', ativo=True)
        self.hoje = timezone.localdate()
        self.dia_hoje = (self.hoje.weekday() + 1) % 7
        self.passeio = Passeio.objects.create(
            hotel=self.hotel,
            dia_semana=self.dia_hoje,
            titulo='City Tour',
            descricao='Passeio pela cidade.',
            hora_saida=time(9, 0),
            ponto_encontro='Recepção',
            vagas=2,
            ativo=True,
        )
        self.hospede = Hospede.objects.create(
            hotel=self.hotel,
            nome_completo='João Turista',
            data_nascimento=date(1990, 5, 10),
            documento='529.982.247-25',
            apartamento='101',
        )
        self.client = Client()
        session = self.client.session
        session['hotel_slug'] = self.hotel.slug
        session.save()

    def _login_gestor(self):
        user = User.objects.create_user('gestor_p', password='testpass123')
        PerfilUsuario.objects.create(
            user=user, papel=PapelUsuario.GERENTE, hotel=self.hotel, ativo=True,
        )
        self.client.login(username='gestor_p', password='testpass123')
        session = self.client.session
        session['hotel_slug'] = self.hotel.slug
        session.save()

    def _login_hospede(self):
        self.client.post(reverse('hospede_app_login'), {
            'apartamento': '101',
            'documento': '24725',
        })

    def test_gestao_lista_passeios(self):
        self._login_gestor()
        resp = self.client.get(reverse('passeios_gestao'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'City Tour')

    def test_gestao_cria_passeio(self):
        self._login_gestor()
        resp = self.client.post(reverse('passeio_novo'), {
            'dia_semana': self.dia_hoje,
            'titulo': 'Cachoeira',
            'descricao': 'Banho de cachoeira.',
            'hora_saida': '10:00',
            'hora_retorno': '13:00',
            'ponto_encontro': 'Lobby',
            'vagas': 0,
            'preco': '',
            'ordem': 1,
            'ativo': 'on',
        })
        self.assertEqual(resp.status_code, 302)
        from core.models import Passeio
        self.assertTrue(Passeio.objects.filter(hotel=self.hotel, titulo='Cachoeira').exists())

    def test_app_hospede_ve_passeios(self):
        self._login_hospede()
        resp = self.client.get(reverse('hospede_app_passeios'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'City Tour')

    def test_app_hospede_inscreve_e_cancela(self):
        from core.models import InscricaoPasseio

        self._login_hospede()
        resp = self.client.post(
            reverse('hospede_app_passeio_inscricao', kwargs={'pk': self.passeio.pk}),
            {'acao': 'inscrever'},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(
            InscricaoPasseio.objects.filter(
                passeio=self.passeio, hospede=self.hospede, data=self.hoje,
            ).exists()
        )

        resp = self.client.post(
            reverse('hospede_app_passeio_inscricao', kwargs={'pk': self.passeio.pk}),
            {'acao': 'cancelar'},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(
            InscricaoPasseio.objects.filter(
                passeio=self.passeio, hospede=self.hospede, data=self.hoje,
            ).exists()
        )

    def test_passeio_lotado_bloqueia(self):
        from core.models import InscricaoPasseio

        self.passeio.vagas = 1
        self.passeio.save()
        outro = Hospede.objects.create(
            hotel=self.hotel,
            nome_completo='Outro Hóspede',
            data_nascimento=date(1988, 1, 1),
            documento='111.444.777-35',
            apartamento='102',
        )
        InscricaoPasseio.objects.create(passeio=self.passeio, hospede=outro, data=self.hoje)

        self.assertTrue(self.passeio.lotado(self.hoje))

        self._login_hospede()
        self.client.post(
            reverse('hospede_app_passeio_inscricao', kwargs={'pk': self.passeio.pk}),
            {'acao': 'inscrever'},
        )
        self.assertFalse(
            InscricaoPasseio.objects.filter(
                passeio=self.passeio, hospede=self.hospede, data=self.hoje,
            ).exists()
        )

    def test_recepcao_inscreve_passeio(self):
        from core.models import InscricaoPasseio

        self._login_gestor()
        resp = self.client.post(reverse('recepcao_vincular_passeio'), {
            'passeio': self.passeio.pk,
            'data': self.hoje.isoformat(),
            'hospedes': [self.hospede.pk],
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(
            InscricaoPasseio.objects.filter(
                passeio=self.passeio, hospede=self.hospede, data=self.hoje,
            ).exists()
        )


import tempfile


@override_settings(ALLOWED_HOSTS=['testserver'], MEDIA_ROOT=tempfile.mkdtemp())
class PagamentoPasseioTestCase(TestCase):
    def setUp(self):
        from core.models import Passeio

        self.hotel = Hotel.objects.create(
            nome='Pix Hotel', slug='dan-inn', ativo=True,
            pix_chave='pix@hotel.com', pix_beneficiario='Hotel Teste',
        )
        self.hoje = timezone.localdate()
        self.dia_hoje = (self.hoje.weekday() + 1) % 7
        self.passeio = Passeio.objects.create(
            hotel=self.hotel,
            dia_semana=self.dia_hoje,
            titulo='Passeio Pago',
            descricao='Passeio com custo.',
            preco='120.00',
            ativo=True,
        )
        self.hospede = Hospede.objects.create(
            hotel=self.hotel,
            nome_completo='Ana Pagante',
            data_nascimento=date(1992, 2, 2),
            documento='529.982.247-25',
            apartamento='201',
        )
        self.client = Client()
        session = self.client.session
        session['hotel_slug'] = self.hotel.slug
        session.save()

    def _login_hospede(self):
        self.client.post(reverse('hospede_app_login'), {
            'apartamento': '201', 'documento': '24725',
        })

    def test_payload_pix_valido(self):
        from core.pix_utils import gerar_payload_pix

        payload = gerar_payload_pix('pix@hotel.com', 'Hotel Teste', 'Pocos de Caldas', valor='120.00', txid='PASSEIO1')
        self.assertTrue(payload.startswith('000201'))
        self.assertIn('br.gov.bcb.pix', payload)
        self.assertIn('5204000053039865406120.00', payload)
        self.assertEqual(len(payload[-4:]), 4)

    def test_inscricao_paga_fica_pendente(self):
        from core.models import InscricaoPasseio, StatusPagamentoPasseio

        self._login_hospede()
        resp = self.client.post(
            reverse('hospede_app_passeio_inscricao', kwargs={'pk': self.passeio.pk}),
            {'acao': 'inscrever'},
        )
        self.assertEqual(resp.status_code, 302)
        insc = InscricaoPasseio.objects.get(passeio=self.passeio, hospede=self.hospede, data=self.hoje)
        self.assertEqual(insc.status_pagamento, StatusPagamentoPasseio.PENDENTE)
        self.assertEqual(str(insc.valor), '120.00')
        self.assertIn('/pagamento/', resp.url)

    def test_pagina_pagamento_mostra_pix(self):
        self._login_hospede()
        self.client.post(
            reverse('hospede_app_passeio_inscricao', kwargs={'pk': self.passeio.pk}),
            {'acao': 'inscrever'},
        )
        resp = self.client.get(reverse('hospede_app_passeio_pagamento', kwargs={'pk': self.passeio.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'copia e cola')
        self.assertContains(resp, 'br.gov.bcb.pix')

    def test_upload_comprovante(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from core.models import InscricaoPasseio, StatusPagamentoPasseio

        self._login_hospede()
        self.client.post(
            reverse('hospede_app_passeio_inscricao', kwargs={'pk': self.passeio.pk}),
            {'acao': 'inscrever'},
        )
        arquivo = SimpleUploadedFile('comprovante.png', b'fakeimagedata', content_type='image/png')
        resp = self.client.post(
            reverse('hospede_app_passeio_pagamento', kwargs={'pk': self.passeio.pk}),
            {'comprovante': arquivo},
        )
        self.assertEqual(resp.status_code, 302)
        insc = InscricaoPasseio.objects.get(passeio=self.passeio, hospede=self.hospede, data=self.hoje)
        self.assertEqual(insc.status_pagamento, StatusPagamentoPasseio.COMPROVANTE_ENVIADO)
        self.assertTrue(insc.comprovante)

    def test_recepcao_confirma_pagamento(self):
        from core.models import InscricaoPasseio, StatusPagamentoPasseio

        insc = InscricaoPasseio.objects.create(
            passeio=self.passeio, hospede=self.hospede, data=self.hoje,
            valor=self.passeio.preco,
            status_pagamento=StatusPagamentoPasseio.COMPROVANTE_ENVIADO,
        )
        user = User.objects.create_user('rec_pag', password='testpass123')
        PerfilUsuario.objects.create(user=user, papel=PapelUsuario.GERENTE, hotel=self.hotel, ativo=True)
        self.client.login(username='rec_pag', password='testpass123')
        session = self.client.session
        session['hotel_slug'] = self.hotel.slug
        session.save()

        resp = self.client.post(reverse('recepcao_passeios_pagamentos'), {
            'inscricao': insc.pk,
            'acao': 'confirmar',
            'status': 'comprovante_enviado',
        })
        self.assertEqual(resp.status_code, 302)
        insc.refresh_from_db()
        self.assertEqual(insc.status_pagamento, StatusPagamentoPasseio.CONFIRMADO)
        self.assertIsNotNone(insc.pagamento_confirmado_em)

    def test_pix_chave_efetiva_fallback(self):
        # passeio sem chave usa a do hotel
        self.assertEqual(self.passeio.pix_chave_efetiva, 'pix@hotel.com')
        self.passeio.pix_chave = 'outra@chave.com'
        self.assertEqual(self.passeio.pix_chave_efetiva, 'outra@chave.com')

    def test_preview_pix_gestao(self):
        user = User.objects.create_user('gestor_pix', password='testpass123')
        PerfilUsuario.objects.create(user=user, papel=PapelUsuario.GERENTE, hotel=self.hotel, ativo=True)
        self.client.login(username='gestor_pix', password='testpass123')
        session = self.client.session
        session['hotel_slug'] = self.hotel.slug
        session.save()

        resp = self.client.get(reverse('passeio_pix_preview'), {
            'valor': '50.00', 'chave': 'teste@pix.com', 'nome': 'Recreacao',
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['ok'])
        self.assertTrue(data['payload'].startswith('000201'))
        self.assertIn('teste@pix.com', data['payload'])


@override_settings(ALLOWED_HOSTS=['testserver'])
class HospedeAppAssistantTestCase(TestCase):
    def setUp(self):
        from core.models import NoiteTematica, Passeio

        self.hotel = Hotel.objects.create(nome='IA Hotel', slug='dan-inn', ativo=True)
        self.hoje = timezone.localdate()
        self.dia_hoje = (self.hoje.weekday() + 1) % 7
        Passeio.objects.create(
            hotel=self.hotel, dia_semana=self.dia_hoje, titulo='Cachoeira Mágica',
            descricao='Banho de cachoeira.', ativo=True,
        )
        NoiteTematica.objects.create(
            hotel=self.hotel, dia_semana=self.dia_hoje, tema='Festa Neon',
            atracao_musical='DJ', descricao_gastronomia='Comidas coloridas',
        )
        self.hospede = Hospede.objects.create(
            hotel=self.hotel, nome_completo='Carla Turista',
            data_nascimento=date(1990, 1, 1), documento='529.982.247-25', apartamento='404',
        )
        self.client = Client()
        session = self.client.session
        session['hotel_slug'] = self.hotel.slug
        session.save()

    def _login(self):
        self.client.post(reverse('hospede_app_login'), {'apartamento': '404', 'documento': '24725'})

    def test_init_requer_login(self):
        resp = self.client.get(reverse('hospede_app_assistant_init'))
        self.assertEqual(resp.status_code, 302)

    def test_init_autenticado(self):
        self._login()
        resp = self.client.get(reverse('hospede_app_assistant_init'))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('Carla', data['greeting'])
        self.assertTrue(len(data['suggestions']) > 0)

    def test_chat_passeios_fallback(self):
        self._login()
        resp = self.client.post(
            reverse('hospede_app_assistant_chat'),
            data=json.dumps({'message': 'quais passeios tem hoje?', 'history': []}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Cachoeira Mágica', resp.json()['reply'])

    def test_chat_noite_fallback(self):
        self._login()
        resp = self.client.post(
            reverse('hospede_app_assistant_chat'),
            data=json.dumps({'message': 'qual a noite tematica?', 'history': []}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Festa Neon', resp.json()['reply'])

from core.models import Recreador, TipoPontoBatida
from core.ponto_service import PontoErro, estado_ponto_hoje, registrar_batida


@override_settings(ALLOWED_HOSTS=['testserver'])
class PontoRecreadorTestCase(TestCase):
    def setUp(self):
        self.hotel = Hotel.objects.create(
            nome='Nacional Inn Test',
            slug='nacional-inn',
            rede_marca='nacional_inn',
        )
        self.rec = Recreador.objects.create(hotel=self.hotel, nome='Ana Rec', ativo=True)
        self.rec.set_pin('1234')
        self.rec.save()
        self.client = Client()
        session = self.client.session
        session['hotel_slug'] = self.hotel.slug
        session.save()

    def test_pin_errado(self):
        with self.assertRaises(PontoErro):
            registrar_batida(recreador=self.rec, hotel=self.hotel, pin='0000')

    def test_entrada_depois_saida(self):
        b1 = registrar_batida(recreador=self.rec, hotel=self.hotel, pin='1234', extra_plantao=True)
        self.assertEqual(b1.tipo, TipoPontoBatida.ENTRADA)
        self.assertTrue(b1.extra_plantao)
        estado = estado_ponto_hoje(self.rec)
        self.assertEqual(estado.proxima_acao, TipoPontoBatida.SAIDA)
        # anti double-tap: force old timestamp
        from django.utils import timezone as tz
        from datetime import timedelta
        b1.registrado_em = tz.now() - timedelta(minutes=2)
        b1.save(update_fields=['registrado_em'])
        b2 = registrar_batida(recreador=self.rec, hotel=self.hotel, pin='1234')
        self.assertEqual(b2.tipo, TipoPontoBatida.SAIDA)

    def test_anti_double_tap(self):
        registrar_batida(recreador=self.rec, hotel=self.hotel, pin='1234')
        with self.assertRaises(PontoErro):
            registrar_batida(recreador=self.rec, hotel=self.hotel, pin='1234')

    def test_quiosque_get(self):
        resp = self.client.get(reverse('ponto_quiosque'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Ana Rec')
