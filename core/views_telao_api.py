from django.conf import settings
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Hospede, Hotel, Passeio, ProgramacaoDiaria
from .serializers import HospedeSerializer, PasseioSerializer, ProgramacaoDiariaSerializer


class TelaoAPIKeyPermission(permissions.BasePermission):
    """Autenticação simples por API key (header X-API-Key ou query ?api_key=)."""

    message = 'API key inválida ou ausente.'

    def has_permission(self, request, view):
        expected = getattr(settings, 'TELAO_API_KEY', '')
        if not expected:
            return False
        provided = request.headers.get('X-API-Key') or request.query_params.get('api_key')
        return provided == expected


def _dia_semana_hoje() -> int:
    """Converte weekday Python (seg=0) para DiaSemana do model (dom=0)."""
    return (timezone.localdate().weekday() + 1) % 7


def _programacao_queryset(hotel_id):
    return (
        ProgramacaoDiaria.objects.filter(hotel_id=hotel_id)
        .select_related('atividade', 'local', 'recreador', 'categoria')
        .annotate(
            presentes_count=Count('presencas', filter=Q(presencas__presente=True)),
            inscritos_count=Count('inscricoes'),
        )
    )


TelaoProgramacaoResponse = inline_serializer(
    name='TelaoProgramacaoResponse',
    fields={
        'hotel_id': serializers.IntegerField(),
        'data': serializers.DateField(),
        'hora_atual': serializers.CharField(),
        'em_andamento': ProgramacaoDiariaSerializer(allow_null=True),
        'proxima': ProgramacaoDiariaSerializer(allow_null=True),
    },
)

TelaoAniversariantesResponse = inline_serializer(
    name='TelaoAniversariantesResponse',
    fields={
        'hotel_id': serializers.IntegerField(),
        'data': serializers.DateField(),
        'total': serializers.IntegerField(),
        'aniversariantes': HospedeSerializer(many=True),
    },
)


class TelaoProgramacaoAtualView(APIView):
    permission_classes = [TelaoAPIKeyPermission]
    authentication_classes = []

    @extend_schema(
        responses=TelaoProgramacaoResponse,
        parameters=[
            OpenApiParameter(name='api_key', location=OpenApiParameter.QUERY, required=False, type=str),
        ],
        tags=['Telão'],
    )
    def get(self, request, hotel_id):
        get_object_or_404(Hotel, pk=hotel_id, ativo=True)
        hoje = timezone.localdate()
        agora = timezone.localtime().time()
        qs = _programacao_queryset(hotel_id).filter(data=hoje).order_by('hora_inicio')

        em_andamento = qs.filter(hora_inicio__lte=agora, hora_fim__gt=agora).first()
        proxima = qs.filter(hora_inicio__gt=agora).first()

        serializer = ProgramacaoDiariaSerializer
        return Response({
            'hotel_id': hotel_id,
            'data': hoje.isoformat(),
            'hora_atual': agora.strftime('%H:%M:%S'),
            'em_andamento': serializer(em_andamento).data if em_andamento else None,
            'proxima': serializer(proxima).data if proxima else None,
        })


class TelaoAniversariantesHojeView(APIView):
    permission_classes = [TelaoAPIKeyPermission]
    authentication_classes = []

    @extend_schema(
        responses=TelaoAniversariantesResponse,
        parameters=[
            OpenApiParameter(name='api_key', location=OpenApiParameter.QUERY, required=False, type=str),
        ],
        tags=['Telão'],
    )
    def get(self, request, hotel_id):
        get_object_or_404(Hotel, pk=hotel_id, ativo=True)
        hoje = timezone.localdate()
        hospedes = (
            Hospede.objects.filter(hotel_id=hotel_id)
            .filter(data_nascimento__month=hoje.month, data_nascimento__day=hoje.day)
            .filter(Q(data_checkout__isnull=True) | Q(data_checkout__gte=hoje))
            .order_by('nome_completo')
        )
        return Response({
            'hotel_id': hotel_id,
            'data': hoje.isoformat(),
            'total': hospedes.count(),
            'aniversariantes': HospedeSerializer(hospedes, many=True).data,
        })


TelaoPasseiosResponse = inline_serializer(
    name='TelaoPasseiosResponse',
    fields={
        'hotel_id': serializers.IntegerField(),
        'dia_semana': serializers.IntegerField(),
        'dia_semana_label': serializers.CharField(),
        'total': serializers.IntegerField(),
        'passeios': PasseioSerializer(many=True),
    },
)


class TelaoPasseiosHojeView(APIView):
    permission_classes = [TelaoAPIKeyPermission]
    authentication_classes = []

    @extend_schema(
        responses=TelaoPasseiosResponse,
        parameters=[
            OpenApiParameter(name='api_key', location=OpenApiParameter.QUERY, required=False, type=str),
        ],
        tags=['Telão'],
    )
    def get(self, request, hotel_id):
        get_object_or_404(Hotel, pk=hotel_id, ativo=True)
        dia = _dia_semana_hoje()
        passeios = Passeio.objects.filter(
            hotel_id=hotel_id, dia_semana=dia, ativo=True,
        ).order_by('ordem', 'titulo')
        from .models import DiaSemana
        label = dict(DiaSemana.choices).get(dia, '')
        return Response({
            'hotel_id': hotel_id,
            'dia_semana': dia,
            'dia_semana_label': label,
            'total': passeios.count(),
            'passeios': PasseioSerializer(passeios, many=True).data,
        })
