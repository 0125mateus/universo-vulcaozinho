from django.conf import settings
from django.contrib.auth import login


class DevAutoLoginMiddleware:
    """Em desenvolvimento, entra automaticamente como superusuário (sem tela de login)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            settings.DEBUG
            and getattr(settings, 'DEV_SKIP_LOGIN', False)
            and not request.user.is_authenticated
        ):
            from django.contrib.auth import get_user_model

            user = get_user_model().objects.filter(is_superuser=True, is_active=True).first()
            if user:
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')

        return self.get_response(request)
