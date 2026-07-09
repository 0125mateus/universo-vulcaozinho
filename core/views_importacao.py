from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views import View

from .analise_faixas import cruzar_banco, cruzar_planilha
from .auth_utils import resolver_hotel_atual
from .forms_importacao import AnaliseFaixasForm, ImportacaoEventosForm, ImportacaoProgramacaoForm
from .importacao_xlsx import importar_eventos, importar_programacao
from .mixins import PapelRequeridoMixin
from .models import EventoRecreacao, PapelUsuario, ProgramacaoDiaria

PAPEIS_IMPORTACAO = [
    PapelUsuario.ADMIN,
    PapelUsuario.DIRETOR,
    PapelUsuario.GERENTE,
    PapelUsuario.SUPERVISOR,
]


class ImportacaoGestaoView(PapelRequeridoMixin, View):
    """Upload de planilhas Excel — programação e eventos."""
    papeis_requeridos = PAPEIS_IMPORTACAO
    titulo_acesso = 'Importação de planilhas'

    def get(self, request):
        hotel = resolver_hotel_atual(request)
        if not hotel:
            messages.error(request, 'Selecione um hotel antes de importar.')
            return redirect('home')

        hoje = timezone.localdate()
        return render(request, 'gestao/importacao.html', {
            'hotel': hotel,
            'form_prog': ImportacaoProgramacaoForm(),
            'form_eventos': ImportacaoEventosForm(),
            'ultima_prog': ProgramacaoDiaria.objects.filter(hotel=hotel).order_by('-data').first(),
            'qtd_eventos': EventoRecreacao.objects.filter(hotel=hotel).count(),
            'eventos_proximos': EventoRecreacao.objects.filter(
                hotel=hotel, data_inicio__gte=hoje,
            ).order_by('data_inicio')[:8],
        })

    def post(self, request):
        hotel = resolver_hotel_atual(request)
        if not hotel:
            messages.error(request, 'Selecione um hotel.')
            return redirect('importacao_gestao')

        tipo = request.POST.get('tipo_importacao')
        if tipo == 'programacao':
            form = ImportacaoProgramacaoForm(request.POST, request.FILES)
            if form.is_valid():
                resultado = importar_programacao(
                    hotel,
                    form.cleaned_data['arquivo'],
                    substituir_datas=form.cleaned_data['substituir_datas'],
                )
                messages.success(
                    request,
                    f'Programação: {resultado.resumo()}. '
                    f'Abas: {", ".join(resultado.abas_processadas) or "nenhuma"}.',
                )
                for err in resultado.erros[:10]:
                    messages.warning(request, err)
            else:
                messages.error(request, 'Arquivo de programação inválido.')
        elif tipo == 'eventos':
            form = ImportacaoEventosForm(request.POST, request.FILES)
            if form.is_valid():
                resultado = importar_eventos(hotel, form.cleaned_data['arquivo'])
                messages.success(
                    request,
                    f'Eventos: {resultado.resumo()}. '
                    f'Abas: {", ".join(resultado.abas_processadas) or "nenhuma"}.',
                )
                for err in resultado.erros[:10]:
                    messages.warning(request, err)
            else:
                messages.error(request, 'Arquivo de eventos inválido.')
        else:
            messages.error(request, 'Tipo de importação desconhecido.')

        return redirect('importacao_gestao')


class EventosRecreacaoListView(PapelRequeridoMixin, View):
    papeis_requeridos = PAPEIS_IMPORTACAO
    titulo_acesso = 'Eventos de recreação'

    def get(self, request):
        hotel = resolver_hotel_atual(request)
        if not hotel:
            return redirect('home')

        mes = request.GET.get('mes')
        qs = EventoRecreacao.objects.filter(hotel=hotel).order_by('-data_inicio')
        if mes:
            qs = qs.filter(mes_referencia__icontains=mes)

        return render(request, 'gestao/eventos_list.html', {
            'hotel': hotel,
            'eventos': qs[:200],
            'total': qs.count(),
            'mes_filtro': mes or '',
        })


class AnaliseFaixasView(PapelRequeridoMixin, View):
    """Cruzamento atividade × faixa etária (planilha ou banco)."""
    papeis_requeridos = PAPEIS_IMPORTACAO
    titulo_acesso = 'Análise de faixas etárias'

    def get(self, request):
        hotel = resolver_hotel_atual(request)
        if not hotel:
            return redirect('home')
        return render(request, 'gestao/analise_faixas.html', {
            'hotel': hotel,
            'form': AnaliseFaixasForm(),
            'resultado': None,
        })

    def post(self, request):
        hotel = resolver_hotel_atual(request)
        if not hotel:
            return redirect('home')

        form = AnaliseFaixasForm(request.POST, request.FILES)
        resultado = None
        if form.is_valid():
            fonte = form.cleaned_data['fonte']
            if fonte == AnaliseFaixasForm.FONTE_PLANILHA:
                arq = form.cleaned_data.get('arquivo')
                if not arq:
                    messages.error(request, 'Selecione uma planilha de programação.')
                else:
                    resultado = cruzar_planilha(arq)
            else:
                dias = form.cleaned_data.get('dias') or 90
                resultado = cruzar_banco(hotel, dias=dias)

            if resultado and resultado.total_linhas == 0:
                messages.warning(request, 'Nenhuma atividade encontrada para análise.')
            elif resultado:
                messages.success(
                    request,
                    f'Análise concluída: {resultado.total_linhas} registros, '
                    f'{len(resultado.faixas)} faixas.',
                )
        else:
            messages.error(request, 'Verifique os dados do formulário.')

        return render(request, 'gestao/analise_faixas.html', {
            'hotel': hotel,
            'form': form,
            'resultado': resultado,
        })
