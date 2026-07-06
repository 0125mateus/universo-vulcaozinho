from django.shortcuts import redirect, render

from django.views import View

from .auth_utils import resolver_hotel_atual
from .mixins import PapelRequeridoMixin
from .models import PapelUsuario


PAPEIS_DASHBOARD = [
    PapelUsuario.ADMIN,
    PapelUsuario.DIRETOR,
    PapelUsuario.GERENTE,
    PapelUsuario.SUPERVISOR,
    PapelUsuario.RECEPCAO,
    PapelUsuario.RECREADOR,
]


class DashboardView(PapelRequeridoMixin, View):
    """
    Dashboard operacional — dados carregados via JS/API (Prompt 5).

    Métricas disponíveis agora (via API):
    - Hóspedes ativos total e por faixa etária
    - Aniversariantes do dia
    - Atividade em andamento + próxima
    - Ocupação (presentes / vagas)
    - Passeios do dia e passaportes com carimbos
    - Vendas da loja / estoque

    Métricas futuras:
    - Financeiro / KPIs executivos (módulo futuro)
    """

    papeis_requeridos = PAPEIS_DASHBOARD
    titulo_acesso = 'Dashboard Operacional'
    login_url = '/entrar/'

    def get(self, request):
        hotel = resolver_hotel_atual(request)
        if not hotel:
            return redirect('home')
        from django.utils import timezone
        hoje = timezone.localdate()
        dia_semana = (hoje.weekday() + 1) % 7
        return render(request, 'dashboard/index.html', {
            'hotel_id': hotel.id,
            'hoje_iso': hoje.isoformat(),
            'dia_semana': dia_semana,
        })
