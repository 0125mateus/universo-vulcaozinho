from django.db.models import Count, Q, Sum

from django.shortcuts import redirect, render

from django.utils import timezone

from django.views import View



from .auth_utils import resolver_hotel_atual

from .mixins import PapelRequeridoMixin

from .financeiro import kpis_financeiros_loja
from .models import Hospede, PapelUsuario, Passeio, PassaporteHospede, ProdutoLoja, ProgramacaoDiaria



PAPEIS_EXECUTIVO = [

    PapelUsuario.ADMIN,

    PapelUsuario.DIRETOR,

    PapelUsuario.GERENTE,

]





class DashboardExecutivoView(PapelRequeridoMixin, View):

    """

    Dashboard executivo / financeiro (visão gerencial).

    KPIs calculados dos módulos operacionais já implementados.

    Receita e margem dependem de módulo financeiro futuro (placeholder).

    """



    papeis_requeridos = PAPEIS_EXECUTIVO

    titulo_acesso = 'Dashboard Executivo'

    login_url = '/entrar/'



    def get(self, request):

        hotel = resolver_hotel_atual(request)

        if not hotel:

            return redirect('home')



        hoje = timezone.localdate()

        dia_semana = (hoje.weekday() + 1) % 7

        hospedes_qs = Hospede.objects.filter(hotel=hotel).filter(

            Q(data_checkout__isnull=True) | Q(data_checkout__gte=hoje)

        )

        programacoes = ProgramacaoDiaria.objects.filter(hotel=hotel, data=hoje)

        produtos = ProdutoLoja.objects.filter(

            Q(hotel=hotel) | Q(hotel__isnull=True), ativo=True,

        )

        passeios_hoje = Passeio.objects.filter(

            hotel=hotel, dia_semana=dia_semana, ativo=True,

        )

        passaportes = PassaporteHospede.objects.filter(hospede__hotel=hotel).annotate(

            carimbos_count=Count('carimbos'),

        )

        passaportes_com_carimbo = passaportes.filter(carimbos_count__gte=1).count()

        passaportes_completos = passaportes.filter(carimbos_count__gte=7).count()

        moedas_totais = passaportes.aggregate(total=Sum('moedas'))['total'] or 0

        fin = kpis_financeiros_loja(hotel)



        estoque_total = produtos.aggregate(total=Sum('estoque'))['total'] or 0

        estoque_baixo = produtos.filter(estoque__lte=5).count()



        ocupacao_media = 0

        progs = programacoes.annotate(

            presentes_count=Count('presencas', filter=Q(presencas__presente=True)),

        )

        if progs.exists():

            total_pct = sum(

                min(100, int((p.presentes_count / p.vagas_total) * 100)) if p.vagas_total else 0

                for p in progs

            )

            ocupacao_media = round(total_pct / progs.count())



        return render(request, 'dashboard/executivo.html', {

            'hotel': hotel,

            'hospedes_ativos': hospedes_qs.count(),

            'atividades_hoje': programacoes.count(),

            'ocupacao_media': ocupacao_media,

            'produtos_ativos': produtos.count(),

            'estoque_total': estoque_total,

            'estoque_baixo': estoque_baixo,

            'passeios_hoje': passeios_hoje.count(),

            'passeio_destaque': passeios_hoje.first(),

            'passaportes_com_carimbo': passaportes_com_carimbo,

            'passaportes_completos': passaportes_completos,

            'moedas_totais': moedas_totais,

            'fin': fin,

        })

