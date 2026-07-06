from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from core.viewsets import (
    AtividadeViewSet,
    HospedeViewSet,
    HotelViewSet,
    PasseioViewSet,
    PassaporteHospedeViewSet,
    PresencaRegistroViewSet,
    ProdutoLojaViewSet,
    ProgramacaoDiariaViewSet,
    VendaLojaViewSet,
)
from core.views_telao_api import (
    TelaoAniversariantesHojeView,
    TelaoPasseiosHojeView,
    TelaoProgramacaoAtualView,
)

router = DefaultRouter()
router.register('hoteis', HotelViewSet, basename='hotel')
router.register('hospedes', HospedeViewSet, basename='hospede')
router.register('atividades', AtividadeViewSet, basename='atividade')
router.register('programacao', ProgramacaoDiariaViewSet, basename='programacao')
router.register('presencas', PresencaRegistroViewSet, basename='presenca')
router.register('produtos', ProdutoLojaViewSet, basename='produto')
router.register('passeios', PasseioViewSet, basename='passeio')
router.register('passaportes', PassaporteHospedeViewSet, basename='passaporte')
router.register('vendas', VendaLojaViewSet, basename='venda')

urlpatterns = [
    path('', include(router.urls)),
    path(
        'telao/<int:hotel_id>/programacao-atual/',
        TelaoProgramacaoAtualView.as_view(),
        name='telao-programacao-atual',
    ),
    path(
        'telao/<int:hotel_id>/aniversariantes-hoje/',
        TelaoAniversariantesHojeView.as_view(),
        name='telao-aniversariantes',
    ),
    path(
        'telao/<int:hotel_id>/passeios-hoje/',
        TelaoPasseiosHojeView.as_view(),
        name='telao-passeios-hoje',
    ),
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='docs'),
]
