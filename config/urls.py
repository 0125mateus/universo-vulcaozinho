from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve as media_serve

from core import views
from core import views_assistant
from core import views_auth
from core import views_dashboard
from core import views_media
from core import views_dashboard_executivo

from core import views_loja

from core import views_noites_gestao

from core import views_passaporte_gestao

from core import views_recepcao

from core import views_reuniao

from core import views_importacao
from core import views_programacao
from core import views_programacao_gestao
from core import views_passeios_gestao
from core import views_telao
from core import views_hospede_app
from core import views_financeiro_operacional
from core import views_ponto



admin.site.site_header = 'Universo Vulcãozinho'

admin.site.site_title = 'Vulcãozinho Admin'

admin.site.index_title = 'Sistema de Recreação Multi-hotel'



urlpatterns = [

    path('', views.HomeView.as_view(), name='home'),

    path('programacao/', views.ProgramacaoView.as_view(), name='programacao'),
    path('programacao/gestao/', views_programacao_gestao.ProgramacaoGestaoListView.as_view(), name='programacao_gestao'),
    path('programacao/gestao/nova/', views_programacao_gestao.ProgramacaoCreateView.as_view(), name='programacao_nova'),
    path('programacao/gestao/novas/', views_programacao_gestao.ProgramacaoBulkCreateView.as_view(), name='programacao_novas'),
    path('programacao/gestao/lote/', views_programacao_gestao.ProgramacaoBulkActionView.as_view(), name='programacao_acao_lote'),
    path('programacao/gestao/<int:pk>/editar/', views_programacao_gestao.ProgramacaoUpdateView.as_view(), name='programacao_editar'),
    path('programacao/gestao/<int:pk>/excluir/', views_programacao_gestao.ProgramacaoDeleteView.as_view(), name='programacao_excluir'),
    path('programacao/publicar-telao/', views_programacao.PublicarTelaoGradeView.as_view(), name='programacao_publicar_telao'),
    path('programacao/remover-telao/', views_programacao.RemoverTelaoGradeView.as_view(), name='programacao_remover_telao'),

    path('passeios/gestao/', views_passeios_gestao.PasseiosGestaoListView.as_view(), name='passeios_gestao'),
    path('passeios/gestao/novo/', views_passeios_gestao.PasseioCreateView.as_view(), name='passeio_novo'),
    path('passeios/gestao/pix-preview/', views_passeios_gestao.PasseioPixPreviewView.as_view(), name='passeio_pix_preview'),
    path('passeios/gestao/<int:pk>/editar/', views_passeios_gestao.PasseioUpdateView.as_view(), name='passeio_editar'),
    path('passeios/gestao/<int:pk>/excluir/', views_passeios_gestao.PasseioDeleteView.as_view(), name='passeio_excluir'),

    path('noites/', views.NoitesView.as_view(), name='noites'),

    path('noites/gestao/', views_noites_gestao.NoitesGestaoListView.as_view(), name='noites_gestao'),

    path('noites/gestao/<int:pk>/', views_noites_gestao.NoiteTematicaUpdateView.as_view(), name='noites_gestao_editar'),

    path('loja/', views.LojaView.as_view(), name='loja'),

    path('loja/gestao/', views_loja.LojaGestaoView.as_view(), name='loja_gestao'),

    path('loja/gestao/novo/', views_loja.ProdutoCreateView.as_view(), name='loja_produto_novo'),

    path('loja/gestao/<int:pk>/', views_loja.ProdutoUpdateView.as_view(), name='loja_produto_editar'),

    path('loja/gestao/<int:pk>/qr/', views_loja.ProdutoQRView.as_view(), name='loja_produto_qr'),

    path('loja/gestao/<int:pk>/venda/', views_loja.ProdutoVendaView.as_view(), name='loja_produto_venda'),

    path('loja/vendas/', views_loja.VendasLojaView.as_view(), name='loja_vendas'),

    path('loja/pdv/', views_loja.LojaPDVView.as_view(), name='loja_pdv'),

    path('loja/financeiro/', views_loja.FinanceiroLojaView.as_view(), name='loja_financeiro'),

    path('financeiro/', views_financeiro_operacional.FinanceiroHubView.as_view(), name='financeiro_hub'),
    path('financeiro/planilha/<str:token>/', views_financeiro_operacional.FinanceiroPlanilhaPublicaView.as_view(), name='financeiro_planilha_publica'),
    path('financeiro/periodo/novo/<str:tipo>/', views_financeiro_operacional.PeriodoCreateView.as_view(), name='financeiro_periodo_novo'),
    path('financeiro/extras/', views_financeiro_operacional.ExtrasListaView.as_view(), name='financeiro_extras_lista'),
    path('financeiro/extras/<int:pk>/', views_financeiro_operacional.ExtrasRecreadoresPeriodoView.as_view(), name='financeiro_extras_periodo'),
    path('financeiro/extras/<int:pk>/exportar/', views_financeiro_operacional.ExtrasRecreadoresExportView.as_view(), name='financeiro_extras_exportar'),
    path('financeiro/atracoes/', views_financeiro_operacional.AtracoesListaView.as_view(), name='financeiro_atracoes_lista'),
    path('financeiro/atracoes/<int:pk>/', views_financeiro_operacional.AtracoesPeriodoView.as_view(), name='financeiro_atracoes_periodo'),
    path('financeiro/atracoes/<int:pk>/exportar/', views_financeiro_operacional.AtracoesExportView.as_view(), name='financeiro_atracoes_exportar'),
    path('financeiro/atracoes/<int:periodo_pk>/novo/', views_financeiro_operacional.PagamentoAtracaoCreateView.as_view(), name='financeiro_atracao_novo'),
    path('financeiro/atracoes/<int:periodo_pk>/<int:pagamento_pk>/editar/', views_financeiro_operacional.PagamentoAtracaoUpdateView.as_view(), name='financeiro_atracao_editar'),
    path('financeiro/atracoes/<int:periodo_pk>/<int:pagamento_pk>/excluir/', views_financeiro_operacional.PagamentoAtracaoDeleteView.as_view(), name='financeiro_atracao_excluir'),
    path('financeiro/compras/', views_financeiro_operacional.ComprasListaView.as_view(), name='financeiro_compras_lista'),
    path('financeiro/compras/<int:pk>/', views_financeiro_operacional.ComprasPeriodoView.as_view(), name='financeiro_compras_periodo'),
    path('financeiro/compras/<int:pk>/exportar/', views_financeiro_operacional.ComprasExportView.as_view(), name='financeiro_compras_exportar'),
    path('financeiro/compras/item/<int:pk>/excluir/', views_financeiro_operacional.ItemCompraDeleteView.as_view(), name='financeiro_compra_excluir'),

    path('faixas/', views.FaixasView.as_view(), name='faixas'),

    path('universo/', views.UniversoView.as_view(), name='universo'),

    path('passaporte/', views.PassaporteView.as_view(), name='passaporte'),

    path('passaporte/gestao/', views_passaporte_gestao.PassaporteGestaoView.as_view(), name='passaporte_gestao'),

    path('dashboard/', views_dashboard.DashboardView.as_view(), name='dashboard'),
    path('dashboard/executivo/', views_dashboard_executivo.DashboardExecutivoView.as_view(), name='dashboard_executivo'),

    path('gestao/importacao/', views_importacao.ImportacaoGestaoView.as_view(), name='importacao_gestao'),
    path('gestao/eventos/', views_importacao.EventosRecreacaoListView.as_view(), name='eventos_gestao'),
    path('gestao/analise-faixas/', views_importacao.AnaliseFaixasView.as_view(), name='analise_faixas'),

    path('telao/', views_telao.TelaoView.as_view(), name='telao'),

    path('app/', views_hospede_app.HospedeAppHomeView.as_view(), name='hospede_app_home'),
    path('app/entrar/', views_hospede_app.HospedeAppLoginView.as_view(), name='hospede_app_login'),
    path('app/identificar-hotel/', views_hospede_app.HospedeAppIdentificarHotelView.as_view(), name='hospede_app_identificar_hotel'),
    path('app/sair/', views_hospede_app.HospedeAppLogoutView.as_view(), name='hospede_app_logout'),
    path('app/programacao/', views_hospede_app.HospedeAppProgramacaoView.as_view(), name='hospede_app_programacao'),
    path('app/passeios/', views_hospede_app.HospedeAppPasseiosView.as_view(), name='hospede_app_passeios'),
    path('app/passeios/<int:pk>/inscricao/', views_hospede_app.HospedeAppPasseioInscricaoView.as_view(), name='hospede_app_passeio_inscricao'),
    path('app/passeios/<int:pk>/pagamento/', views_hospede_app.HospedeAppPasseioPagamentoView.as_view(), name='hospede_app_passeio_pagamento'),
    path('app/passaporte/', views_hospede_app.HospedeAppPassaporteView.as_view(), name='hospede_app_passaporte'),
    path('app/manifest.webmanifest', views_hospede_app.HospedeAppManifestView.as_view(), name='hospede_app_manifest'),
    path('app/assistente/init/', views_hospede_app.HospedeAppAssistantInitView.as_view(), name='hospede_app_assistant_init'),
    path('app/assistente/chat/', views_hospede_app.HospedeAppAssistantChatView.as_view(), name='hospede_app_assistant_chat'),

    path('telao/<int:hotel_id>/', views_telao.TelaoView.as_view(), name='telao_hotel'),

    path('recepcao/', views_recepcao.RecepcaoIndexView.as_view(), name='recepcao_index'),

    path('recepcao/checkin/', views_recepcao.CheckinCreateView.as_view(), name='recepcao_checkin'),

    path('recepcao/hospedes/', views_recepcao.HospedeListView.as_view(), name='recepcao_hospedes'),

    path('recepcao/hospedes/<int:pk>/', views_recepcao.HospedeDetailView.as_view(), name='recepcao_hospede_detalhe'),
    path('recepcao/hospedes/<int:pk>/termo/', views_recepcao.HospedeTermoView.as_view(), name='recepcao_hospede_termo'),

    path('termo/<str:token>/', views_recepcao.HospedeTermoPublicoView.as_view(), name='termo_publico'),
    path('recepcao/hospedes/<int:pk>/checkout/', views_recepcao.HospedeCheckoutView.as_view(), name='recepcao_checkout'),
    path('recepcao/hospedes/<int:pk>/excluir/', views_recepcao.HospedeDeleteView.as_view(), name='recepcao_hospede_excluir'),

    path('recepcao/agenda/', views_recepcao.AgendaDiaView.as_view(), name='recepcao_agenda'),

    path('recepcao/presenca/<int:pk>/', views_recepcao.RegistrarPresencaView.as_view(), name='recepcao_presenca'),

    path('recepcao/vincular/', views_recepcao.VincularAtividadeView.as_view(), name='recepcao_vincular'),

    path('recepcao/passeios/', views_recepcao.VincularPasseioView.as_view(), name='recepcao_vincular_passeio'),
    path('recepcao/passeios/pagamentos/', views_recepcao.PagamentosPasseioView.as_view(), name='recepcao_passeios_pagamentos'),

    path('api/recepcao/faixa-preview/', views_recepcao.FaixaEtariaPreviewAPI.as_view(), name='recepcao_faixa_preview'),

    path('reuniao/', views_reuniao.ReuniaoView.as_view(), name='reuniao'),

    path('api/reuniao/mensagens/', views_reuniao.ReuniaoMensagensAPI.as_view(), name='reuniao_mensagens'),

    path('api/reuniao/enviar/', views_reuniao.ReuniaoEnviarAPI.as_view(), name='reuniao_enviar'),

    path('hotel/<slug:slug>/', views.selecionar_hotel, name='selecionar_hotel'),

    path('ponto/', views_ponto.PontoQuiosqueView.as_view(), name='ponto_quiosque'),
    path('ponto/app/', views_ponto.PontoAppHomeView.as_view(), name='ponto_app_home'),
    path('ponto/app/entrar/', views_ponto.PontoAppLoginView.as_view(), name='ponto_app_login'),
    path('ponto/app/sair/', views_ponto.PontoAppLogoutView.as_view(), name='ponto_app_logout'),
    path('ponto/gestao/', views_ponto.PontoGestaoView.as_view(), name='ponto_gestao'),
    path('ponto/gestao/exportar/xlsx/', views_ponto.PontoExportXlsxView.as_view(), name='ponto_export_xlsx'),
    path('ponto/gestao/exportar/pdf/', views_ponto.PontoExportPdfView.as_view(), name='ponto_export_pdf'),
    path('ponto/gestao/novo/', views_ponto.PontoRecreadorNovoView.as_view(), name='ponto_recreador_novo'),
    path('ponto/gestao/<int:pk>/', views_ponto.PontoRecreadorConfigView.as_view(), name='ponto_recreador_config'),
    path('ponto/gestao/<int:pk>/excluir/', views_ponto.PontoRecreadorExcluirView.as_view(), name='ponto_recreador_excluir'),
    path('ponto/api/autenticar/', views_ponto.PontoAutenticarAPI.as_view(), name='ponto_api_autenticar'),
    path('ponto/api/<int:pk>/estado/', views_ponto.PontoRecreadorEstadoAPI.as_view(), name='ponto_api_estado'),
    path('ponto/api/<int:pk>/rosto/', views_ponto.PontoVerificarRostoAPI.as_view(), name='ponto_api_rosto'),
    path('ponto/api/<int:pk>/registrar/', views_ponto.PontoRegistrarAPI.as_view(), name='ponto_api_registrar'),

    path('api/assistant/init/', views_assistant.assistant_init, name='assistant_init'),

    path('api/assistant/chat/', views_assistant.assistant_chat_view, name='assistant_chat'),

    path('api/v1/', include('config.api_urls')),

    path('entrar/', views_auth.LoginView.as_view(), name='login'),

    path('sair/', views_auth.LogoutView.as_view(), name='logout'),

    path('senha/esqueci/', views_auth.PasswordResetView.as_view(), name='password_reset'),

    path('senha/enviado/', views_auth.PasswordResetDoneView.as_view(), name='password_reset_done'),

    path('senha/redefinir/<uidb64>/<token>/', views_auth.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),

    path('senha/concluido/', views_auth.PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    path('admin/', admin.site.urls),
    path('media-db/<path:name>', views_media.MediaDbServeView.as_view(), name='media_db_serve'),

]

# Em produção (Render) o helper static() não registra MEDIA; precisamos servir uploads.
urlpatterns += [
    re_path(
        r'^media/(?P<path>.*)$',
        media_serve,
        {'document_root': settings.MEDIA_ROOT},
    ),
]


