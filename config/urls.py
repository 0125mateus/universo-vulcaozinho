from django.contrib import admin

from django.urls import include, path



from core import views

from core import views_assistant

from core import views_auth

from core import views_dashboard
from core import views_dashboard_executivo

from core import views_loja

from core import views_noites_gestao

from core import views_passaporte_gestao

from core import views_recepcao

from core import views_reuniao

from core import views_telao



admin.site.site_header = 'Universo Vulcãozinho'

admin.site.site_title = 'Vulcãozinho Admin'

admin.site.index_title = 'Sistema de Recreação Multi-hotel'



urlpatterns = [

    path('', views.HomeView.as_view(), name='home'),

    path('programacao/', views.ProgramacaoView.as_view(), name='programacao'),

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

    path('faixas/', views.FaixasView.as_view(), name='faixas'),

    path('universo/', views.UniversoView.as_view(), name='universo'),

    path('passaporte/', views.PassaporteView.as_view(), name='passaporte'),

    path('passaporte/gestao/', views_passaporte_gestao.PassaporteGestaoView.as_view(), name='passaporte_gestao'),

    path('dashboard/', views_dashboard.DashboardView.as_view(), name='dashboard'),
    path('dashboard/executivo/', views_dashboard_executivo.DashboardExecutivoView.as_view(), name='dashboard_executivo'),

    path('telao/', views_telao.TelaoView.as_view(), name='telao'),

    path('telao/<int:hotel_id>/', views_telao.TelaoView.as_view(), name='telao_hotel'),

    path('recepcao/', views_recepcao.RecepcaoIndexView.as_view(), name='recepcao_index'),

    path('recepcao/checkin/', views_recepcao.CheckinCreateView.as_view(), name='recepcao_checkin'),

    path('recepcao/hospedes/', views_recepcao.HospedeListView.as_view(), name='recepcao_hospedes'),

    path('recepcao/hospedes/<int:pk>/checkout/', views_recepcao.HospedeCheckoutView.as_view(), name='recepcao_checkout'),

    path('recepcao/agenda/', views_recepcao.AgendaDiaView.as_view(), name='recepcao_agenda'),

    path('recepcao/presenca/<int:pk>/', views_recepcao.RegistrarPresencaView.as_view(), name='recepcao_presenca'),

    path('recepcao/vincular/', views_recepcao.VincularAtividadeView.as_view(), name='recepcao_vincular'),

    path('api/recepcao/faixa-preview/', views_recepcao.FaixaEtariaPreviewAPI.as_view(), name='recepcao_faixa_preview'),

    path('reuniao/', views_reuniao.ReuniaoView.as_view(), name='reuniao'),

    path('api/reuniao/mensagens/', views_reuniao.ReuniaoMensagensAPI.as_view(), name='reuniao_mensagens'),

    path('api/reuniao/enviar/', views_reuniao.ReuniaoEnviarAPI.as_view(), name='reuniao_enviar'),

    path('hotel/<slug:slug>/', views.selecionar_hotel, name='selecionar_hotel'),

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

]


