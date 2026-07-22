"""Envia um e-mail de teste via SMTP configurado (Render Shell)."""

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Testa envio SMTP. Uso: python manage.py test_email seu@email.com'

    def add_arguments(self, parser):
        parser.add_argument('destino', nargs='?', default='', help='E-mail de destino')

    def handle(self, *args, **options):
        destino = (options.get('destino') or '').strip() or getattr(settings, 'EMAIL_HOST_USER', '')
        if not destino:
            self.stderr.write('Informe o e-mail: python manage.py test_email voce@gmail.com')
            return

        self.stdout.write(f'Backend: {settings.EMAIL_BACKEND}')
        self.stdout.write(f'HOST: {getattr(settings, "EMAIL_HOST", "(não definido)")}')
        self.stdout.write(f'USER: {getattr(settings, "EMAIL_HOST_USER", "")}')
        self.stdout.write(f'FROM: {settings.DEFAULT_FROM_EMAIL}')
        self.stdout.write(f'Destino: {destino}')

        if 'console' in settings.EMAIL_BACKEND:
            self.stderr.write(self.style.ERROR(
                'SMTP não configurado (EMAIL_HOST vazio). E-mails vão para o console.'
            ))

        try:
            n = send_mail(
                subject='Recrear — teste de e-mail',
                message=(
                    'Se você recebeu esta mensagem, o SMTP do Recrear está funcionando.\n\n'
                    '— Sistema Recrear'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[destino],
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS(f'Envio OK ({n} mensagem). Confira a caixa e o spam.'))
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f'Falha SMTP: {exc}'))
