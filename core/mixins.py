from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import render

from .auth_utils import filtrar_queryset_por_hotel, get_hotel_escopo, usuario_tem_papel


class HotelScopedMixin:
    """
    Filtra queryset por hotel do PerfilUsuario.
    Admin/Diretor sem hotel = vê todos.
    """

    hotel_campo = 'hotel'

    def get_queryset(self):
        qs = super().get_queryset()
        return filtrar_queryset_por_hotel(qs, self.request.user, self.hotel_campo)

    def get_hotel_contexto(self):
        return get_hotel_escopo(self.request.user)


class PapelRequeridoMixin(LoginRequiredMixin):
    """Restringe view aos papéis listados (+ Admin e superuser)."""

    papeis_requeridos: list[str] = []
    login_url = '/entrar/'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not usuario_tem_papel(request.user, self.papeis_requeridos):
            return render(
                request,
                'core/acesso_negado.html',
                {
                    'papeis_necessarios': self.papeis_requeridos,
                    'titulo': getattr(self, 'titulo_acesso', 'Acesso restrito'),
                },
                status=403,
            )
        return super().dispatch(request, *args, **kwargs)


class StaffHotelMixin(HotelScopedMixin, LoginRequiredMixin):
    """CBV autenticada com escopo de hotel (Prompt 3)."""
    login_url = '/entrar/'
