from django.conf import settings
from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.forms import PasswordResetForm
from django.urls import reverse_lazy
import logging

logger = logging.getLogger(__name__)


def _email_configurado() -> bool:
    return bool(getattr(settings, 'EMAIL_HOST', '').strip()) and (
        settings.EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend'
    )


class LoginView(auth_views.LoginView):
    template_name = 'auth/login.html'
    redirect_authenticated_user = True
    next_page = reverse_lazy('home')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['email_configurado'] = _email_configurado()
        return ctx


class LogoutView(auth_views.LogoutView):
    next_page = reverse_lazy('home')


class PasswordResetView(auth_views.PasswordResetView):
    template_name = 'auth/password_reset.html'
    email_template_name = 'auth/password_reset_email.txt'
    subject_template_name = 'auth/password_reset_subject.txt'
    success_url = reverse_lazy('password_reset_done')
    form_class = PasswordResetForm

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['email_configurado'] = _email_configurado()
        return ctx

    def form_valid(self, form):
        email = form.cleaned_data.get('email', '')
        users = list(form.get_users(email))
        if not users:
            logger.warning('Password reset: nenhum usuário com e-mail %s', email)
        try:
            return super().form_valid(form)
        except Exception as exc:
            logger.exception('Password reset SMTP falhou: %s', exc)
            messages.error(
                self.request,
                'Não foi possível enviar o e-mail. Verifique SMTP no Render ou tente mais tarde.',
            )
            return self.form_invalid(form)


class PasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = 'auth/password_reset_done.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['email_configurado'] = _email_configurado()
        return ctx


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = 'auth/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')


class PasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = 'auth/password_reset_complete.html'
