from django.db.models import Count, Q
from rest_framework import viewsets

from .auth_utils import filtrar_queryset_por_hotel, get_hotel_escopo
from .models import Atividade, Hospede, Hotel, Passeio, PassaporteHospede, PresencaRegistro, ProdutoLoja, ProgramacaoDiaria, VendaLoja
from .permissions import HotelScopedPermission
from .serializers import (
    AtividadeSerializer,
    HospedeSerializer,
    HotelSerializer,
    PasseioSerializer,
    PassaporteHospedeSerializer,
    PresencaRegistroSerializer,
    ProdutoLojaSerializer,
    ProgramacaoDiariaSerializer,
    VendaLojaSerializer,
)


class HotelScopedViewSetMixin:
    """Filtra queryset pelo hotel do PerfilUsuario (mesma lógica do HotelScopedMixin)."""

    hotel_campo = 'hotel'

    def get_queryset(self):
        qs = super().get_queryset()
        return filtrar_queryset_por_hotel(qs, self.request.user, self.hotel_campo)

    def perform_create(self, serializer):
        hotel = get_hotel_escopo(self.request.user)
        if hotel and self.hotel_campo == 'hotel':
            serializer.save(hotel=hotel)
        else:
            serializer.save()


class HotelViewSet(viewsets.ModelViewSet):
    serializer_class = HotelSerializer
    permission_classes = [HotelScopedPermission]
    http_method_names = ['get', 'head', 'options']

    def get_queryset(self):
        qs = Hotel.objects.filter(ativo=True)
        hotel = get_hotel_escopo(self.request.user)
        if hotel:
            qs = qs.filter(pk=hotel.pk)
        return qs


class HospedeViewSet(HotelScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Hospede.objects.select_related('hotel').all()
    serializer_class = HospedeSerializer
    permission_classes = [HotelScopedPermission]

    def get_queryset(self):
        qs = super().get_queryset()
        ativos = self.request.query_params.get('ativos')
        if ativos in ('1', 'true', 'yes'):
            from django.utils import timezone
            hoje = timezone.localdate()
            qs = qs.filter(
                Q(data_checkout__isnull=True) | Q(data_checkout__gte=hoje)
            )
        q = self.request.query_params.get('q')
        if q:
            qs = qs.filter(
                Q(nome_completo__icontains=q) | Q(apartamento__icontains=q)
            )
        return qs


class AtividadeViewSet(HotelScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Atividade.objects.select_related('hotel', 'categoria', 'local_padrao').filter(ativo=True)
    serializer_class = AtividadeSerializer
    permission_classes = [HotelScopedPermission]


class ProgramacaoDiariaViewSet(HotelScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = ProgramacaoDiaria.objects.all()
    serializer_class = ProgramacaoDiariaSerializer
    permission_classes = [HotelScopedPermission]

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.select_related(
            'hotel', 'atividade', 'local', 'recreador', 'categoria'
        ).annotate(
            presentes_count=Count('presencas', filter=Q(presencas__presente=True)),
            inscritos_count=Count('inscricoes'),
        )
        data = self.request.query_params.get('data')
        if data:
            qs = qs.filter(data=data)
        return qs


class PresencaRegistroViewSet(HotelScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = PresencaRegistro.objects.all()
    serializer_class = PresencaRegistroSerializer
    permission_classes = [HotelScopedPermission]
    hotel_campo = 'programacao__hotel'

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.select_related(
            'programacao', 'programacao__hotel', 'hospede', 'registrado_por'
        )
        programacao = self.request.query_params.get('programacao')
        if programacao:
            qs = qs.filter(programacao_id=programacao)
        return qs

    def perform_create(self, serializer):
        serializer.save(registrado_por=self.request.user)


class ProdutoLojaViewSet(viewsets.ModelViewSet):
    serializer_class = ProdutoLojaSerializer
    permission_classes = [HotelScopedPermission]

    def get_queryset(self):
        from django.db.models import Q
        qs = ProdutoLoja.objects.filter(ativo=True)
        hotel = get_hotel_escopo(self.request.user)
        if hotel:
            qs = qs.filter(Q(hotel=hotel) | Q(hotel__isnull=True))
        return qs.order_by('ordem', 'nome')

    def perform_create(self, serializer):
        hotel = get_hotel_escopo(self.request.user)
        if hotel:
            serializer.save(hotel=hotel)
        else:
            serializer.save()


class PasseioViewSet(HotelScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Passeio.objects.filter(ativo=True)
    serializer_class = PasseioSerializer
    permission_classes = [HotelScopedPermission]
    http_method_names = ['get', 'head', 'options']

    def get_queryset(self):
        qs = super().get_queryset()
        dia = self.request.query_params.get('dia')
        if dia is not None:
            qs = qs.filter(dia_semana=dia)
        return qs.order_by('dia_semana', 'ordem')


class PassaporteHospedeViewSet(viewsets.ModelViewSet):
    serializer_class = PassaporteHospedeSerializer
    permission_classes = [HotelScopedPermission]
    http_method_names = ['get', 'head', 'options']

    def get_queryset(self):
        from django.db.models import Count
        qs = PassaporteHospede.objects.select_related('hospede', 'hospede__hotel').annotate(
            total_carimbos=Count('carimbos'),
        )
        hotel = get_hotel_escopo(self.request.user)
        if hotel:
            qs = qs.filter(hospede__hotel=hotel)
        com_carimbo = self.request.query_params.get('com_carimbo')
        if com_carimbo in ('1', 'true', 'yes'):
            qs = qs.filter(total_carimbos__gte=1)
        return qs.order_by('-total_carimbos', 'hospede__nome_completo')


class VendaLojaViewSet(HotelScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = VendaLoja.objects.select_related('produto', 'registrado_por', 'hotel')
    serializer_class = VendaLojaSerializer
    permission_classes = [HotelScopedPermission]
    http_method_names = ['get', 'head', 'options', 'post']

    def get_queryset(self):
        qs = super().get_queryset()
        mes = self.request.query_params.get('mes')
        if mes:
            from django.utils.dateparse import parse_date
            d = parse_date(mes + '-01') if len(mes) == 7 else parse_date(mes)
            if d:
                qs = qs.filter(criado_em__year=d.year, criado_em__month=d.month)
        return qs.order_by('-criado_em')

    def perform_create(self, serializer):
        hotel = get_hotel_escopo(self.request.user)
        serializer.save(
            hotel=hotel,
            registrado_por=self.request.user,
        )
