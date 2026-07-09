from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views import View

from .auth_utils import usuario_tem_papel
from .hoteis import hoteis_rede_queryset
from .views_programacao import PAPEIS_PUBLICAR_TELAO, grade_publicada_hoje
from .models import (
    CategoriaProgramacao,
    Hospede,
    Hotel,
    NoiteTematica,
    ProdutoLoja,
    ProgramacaoDiaria,
)

HORARIOS_FIXOS = [
    ('10:00', 'Início / Boas-vindas'),
    ('13:00', 'Intervalo para Almoço'),
    ('14:00', 'Retorno às Atividades'),
    ('17:00', 'Intervalo / Hora do Lanche'),
    ('17:30', 'Retorno às Atividades'),
    ('21:55', 'Encerramento do Dia'),
]


def selecionar_hotel(request, slug):
    if hoteis_rede_queryset().filter(slug=slug).exists():
        request.session['hotel_slug'] = slug
    return redirect(request.META.get('HTTP_REFERER', '/'))


class HomeView(View):
    def get(self, request):
        hotel = _hotel_atual(request)
        if not hotel:
            return render(request, 'core/home.html', {'sem_hotel': True})

        hoje = timezone.localdate()
        dia_semana = (hoje.weekday() + 1) % 7  # Python seg=0 → nosso dom=0

        noite_hoje = NoiteTematica.objects.filter(hotel=hotel, dia_semana=dia_semana).first()
        programacoes = ProgramacaoDiaria.objects.filter(
            hotel=hotel, data=hoje
        ).select_related('atividade', 'local', 'categoria', 'recreador')[:8]
        hospedes_qs = Hospede.objects.filter(hotel=hotel).filter(
            Q(data_checkout__isnull=True) | Q(data_checkout__gte=hoje)
        )
        hospedes_ativos = hospedes_qs.count()

        faixas = []
        for cat in CategoriaProgramacao.objects.all():
            count = sum(1 for h in hospedes_qs if cat.idade_min <= h.idade <= cat.idade_max)
            faixas.append({'categoria': cat, 'hospedes': count})

        return render(request, 'core/home.html', {
            'noite_hoje': noite_hoje,
            'programacoes': programacoes,
            'hospedes_ativos': hospedes_ativos,
            'faixas': faixas,
            'horarios_fixos': HORARIOS_FIXOS,
        })


class ProgramacaoView(View):
    def get(self, request):
        hotel = _hotel_atual(request)
        if not hotel:
            return redirect('home')

        hoje = timezone.localdate()
        categorias = CategoriaProgramacao.objects.all()
        programacoes = ProgramacaoDiaria.objects.filter(
            hotel=hotel, data=hoje
        ).select_related('atividade', 'local', 'categoria', 'recreador').order_by('hora_inicio')
        total_atividades = programacoes.count()

        grade = {cat.id: [] for cat in categorias}
        sem_categoria = []
        for prog in programacoes:
            if prog.categoria_id and prog.categoria_id in grade:
                grade[prog.categoria_id].append(prog)
            else:
                sem_categoria.append(prog)

        colunas = [{'categoria': cat, 'programacoes': grade.get(cat.id, [])} for cat in categorias]

        pub = grade_publicada_hoje(hotel, hoje)
        pode_gestao = (
            request.user.is_authenticated
            and usuario_tem_papel(request.user, PAPEIS_PUBLICAR_TELAO)
        )

        return render(request, 'core/programacao.html', {
            'colunas': colunas,
            'sem_categoria': sem_categoria,
            'horarios_fixos': HORARIOS_FIXOS,
            'hoje': hoje,
            'total_atividades': total_atividades,
            'pode_publicar_telao': pode_gestao,
            'pode_editar_programacao': pode_gestao,
            'grade_no_telao': pub,
        })


class FaixasView(View):
    """Página das faixas etárias (Ages) da recreação."""

    def get(self, request):
        hotel = _hotel_atual(request)
        hoje = timezone.localdate()
        categorias = CategoriaProgramacao.objects.all()

        faixas_data = []
        hospedes_qs = []
        if hotel:
            hospedes_qs = list(Hospede.objects.filter(hotel=hotel).filter(
                Q(data_checkout__isnull=True) | Q(data_checkout__gte=hoje)
            ))

        for cat in categorias:
            hospedes_count = sum(
                1 for h in hospedes_qs if cat.idade_min <= h.idade <= cat.idade_max
            )
            atividades_hoje = 0
            if hotel:
                atividades_hoje = ProgramacaoDiaria.objects.filter(
                    hotel=hotel, data=hoje, categoria=cat
                ).count()

            faixas_data.append({
                'categoria': cat,
                'hospedes': hospedes_count,
                'atividades_hoje': atividades_hoje,
            })

        return render(request, 'core/faixas.html', {
            'faixas_data': faixas_data,
            'horarios_fixos': HORARIOS_FIXOS,
        })


class UniversoView(View):
    """Visão geral do Universo Vulcãozinho (infográfico)."""

    def get(self, request):
        return render(request, 'core/universo.html')


class NoitesView(View):
    def get(self, request):
        hotel = _hotel_atual(request)
        if not hotel:
            return redirect('home')

        noites = NoiteTematica.objects.filter(hotel=hotel).order_by('dia_semana')
        return render(request, 'core/noites.html', {'noites': noites})


class LojaView(View):
    def get(self, request):
        produtos = ProdutoLoja.objects.filter(ativo=True).order_by('ordem', 'nome')
        acessorios = produtos.filter(categoria='acessorio')
        noites = produtos.filter(categoria='noite_tematica')
        return render(request, 'core/loja.html', {
            'acessorios': acessorios,
            'produtos_noites': noites,
        })


class PassaporteView(View):
    def get(self, request):
        hotel = _hotel_atual(request)
        if not hotel:
            return redirect('home')

        hoje = timezone.localdate()
        hospedes = Hospede.objects.filter(hotel=hotel).filter(
            Q(data_checkout__isnull=True) | Q(data_checkout__gte=hoje)
        ).select_related('passaporte').prefetch_related(
            'passaporte__carimbos__noite_tematica'
        )

        noites = NoiteTematica.objects.filter(hotel=hotel).order_by('dia_semana')
        hospedes_data = []
        for hospede in hospedes:
            carimbo_ids = set()
            if hasattr(hospede, 'passaporte') and hospede.passaporte:
                carimbo_ids = set(
                    hospede.passaporte.carimbos.values_list('noite_tematica_id', flat=True)
                )
            hospedes_data.append({
                'hospede': hospede,
                'carimbo_ids': carimbo_ids,
                'total': len(carimbo_ids),
            })

        return render(request, 'core/passaporte.html', {
            'hospedes_data': hospedes_data,
            'noites': noites,
        })


def _hotel_atual(request):
    slug = request.session.get('hotel_slug')
    if slug:
        return hoteis_rede_queryset().filter(slug=slug).first()
    return hoteis_rede_queryset().first()
