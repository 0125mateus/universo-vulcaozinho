from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from .auth_utils import resolver_hotel_atual
from .mixins import PapelRequeridoMixin
from .models import (
    CarimboPassaporte,
    Hospede,
    NoiteTematica,
    PapelUsuario,
    PassaporteHospede,
)

PAPEIS_PASSAPORTE = [
    PapelUsuario.ADMIN,
    PapelUsuario.DIRETOR,
    PapelUsuario.GERENTE,
    PapelUsuario.SUPERVISOR,
    PapelUsuario.RECEPCAO,
    PapelUsuario.RECREADOR,
]


class PassaporteGestaoView(PapelRequeridoMixin, View):
    papeis_requeridos = PAPEIS_PASSAPORTE
    titulo_acesso = 'Gestão do Passaporte'
    login_url = '/entrar/'

    def get(self, request):
        hotel = resolver_hotel_atual(request)
        if not hotel:
            return redirect('home')

        hoje = timezone.localdate()
        hospedes = Hospede.objects.filter(hotel=hotel).filter(
            Q(data_checkout__isnull=True) | Q(data_checkout__gte=hoje)
        ).select_related('passaporte').prefetch_related('passaporte__carimbos')

        for h in hospedes:
            PassaporteHospede.objects.get_or_create(hospede=h)

        noites = NoiteTematica.objects.filter(hotel=hotel).order_by('dia_semana')
        dia_hoje = (hoje.weekday() + 1) % 7
        noite_hoje = noites.filter(dia_semana=dia_hoje).first()

        dados = []
        for h in hospedes:
            p = h.passaporte
            carimbo_ids = set(p.carimbos.values_list('noite_tematica_id', flat=True))
            dados.append({
                'hospede': h,
                'passaporte': p,
                'carimbo_ids': carimbo_ids,
            })

        return render(request, 'passaporte/gestao.html', {
            'dados': dados,
            'noites': noites,
            'noite_hoje': noite_hoje,
        })

    def post(self, request):
        hotel = resolver_hotel_atual(request)
        if not hotel:
            return redirect('home')

        acao = request.POST.get('acao')
        hospede_id = request.POST.get('hospede_id')

        if acao == 'carimbo':
            noite_id = request.POST.get('noite_id')
            hospede = get_object_or_404(Hospede, pk=hospede_id, hotel=hotel)
            passaporte, _ = PassaporteHospede.objects.get_or_create(hospede=hospede)
            noite = get_object_or_404(NoiteTematica, pk=noite_id, hotel=hotel)
            _, created = CarimboPassaporte.objects.get_or_create(
                passaporte=passaporte,
                noite_tematica=noite,
            )
            if created:
                passaporte.moedas += 10
                passaporte.save(update_fields=['moedas'])
                messages.success(request, f'Carimbo "{noite.tema}" concedido a {hospede.nome_completo}! +10 moedas')
            else:
                messages.info(request, 'Carimbo já existente.')

        elif acao == 'moedas':
            qtd = int(request.POST.get('moedas', 0))
            hospede = get_object_or_404(Hospede, pk=hospede_id, hotel=hotel)
            passaporte, _ = PassaporteHospede.objects.get_or_create(hospede=hospede)
            passaporte.moedas = max(0, passaporte.moedas + qtd)
            passaporte.save(update_fields=['moedas'])
            messages.success(request, f'Moedas atualizadas: {passaporte.moedas}')

        return redirect('passaporte_gestao')
