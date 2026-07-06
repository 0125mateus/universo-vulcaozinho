from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, UpdateView

from .auth_utils import filtrar_queryset_por_hotel, resolver_hotel_atual
from .forms import NoiteTematicaForm
from .mixins import PapelRequeridoMixin
from .models import NoiteTematica, PapelUsuario

PAPEIS_NOITES = [
    PapelUsuario.ADMIN,
    PapelUsuario.DIRETOR,
    PapelUsuario.GERENTE,
    PapelUsuario.SUPERVISOR,
]


class NoitesGestaoMixin(PapelRequeridoMixin):
    papeis_requeridos = PAPEIS_NOITES
    titulo_acesso = 'Gestão de Noites Temáticas'
    login_url = '/entrar/'

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.hotel = resolver_hotel_atual(request)


class NoitesGestaoListView(NoitesGestaoMixin, ListView):
    model = NoiteTematica
    template_name = 'noites/gestao_list.html'
    context_object_name = 'noites'

    def dispatch(self, request, *args, **kwargs):
        if not self.hotel:
            messages.error(request, 'Selecione um hotel.')
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = NoiteTematica.objects.filter(hotel=self.hotel)
        return filtrar_queryset_por_hotel(qs, self.request.user).order_by('dia_semana')


class NoiteTematicaUpdateView(NoitesGestaoMixin, UpdateView):
    model = NoiteTematica
    form_class = NoiteTematicaForm
    template_name = 'noites/gestao_form.html'
    success_url = reverse_lazy('noites_gestao')

    def get_queryset(self):
        qs = NoiteTematica.objects.filter(hotel=self.hotel)
        return filtrar_queryset_por_hotel(qs, self.request.user)

    def form_valid(self, form):
        messages.success(self.request, 'Noite temática atualizada.')
        return super().form_valid(form)
