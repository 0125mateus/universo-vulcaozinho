"""Serve arquivos gravados no banco (DatabaseMediaStorage)."""

from django.http import Http404, HttpResponse
from django.views import View

from .models import StoredMediaFile


class MediaDbServeView(View):
    def get(self, request, name):
        obj = StoredMediaFile.objects.filter(name=name).first()
        if not obj:
            raise Http404('Arquivo não encontrado.')
        response = HttpResponse(bytes(obj.content), content_type=obj.content_type or 'application/octet-stream')
        response['Content-Length'] = str(obj.size or len(obj.content))
        response['Cache-Control'] = 'public, max-age=86400'
        return response
