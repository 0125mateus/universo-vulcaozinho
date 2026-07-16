"""Armazena uploads no banco (PostgreSQL) para sobreviver a redeploys no Render free."""

from __future__ import annotations

import mimetypes

from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.db import transaction
from django.urls import reverse
from django.utils.deconstruct import deconstructible


@deconstructible
class DatabaseMediaStorage(Storage):
    """Storage que grava bytes em core.StoredMediaFile."""

    def _get_model(self):
        from core.models import StoredMediaFile
        return StoredMediaFile

    def _open(self, name, mode='rb'):
        StoredMediaFile = self._get_model()
        obj = StoredMediaFile.objects.filter(name=name).first()
        if not obj:
            raise FileNotFoundError(name)
        return ContentFile(bytes(obj.content), name=name)

    def _save(self, name, content):
        StoredMediaFile = self._get_model()
        if hasattr(content, 'chunks'):
            data = b''.join(chunk for chunk in content.chunks())
        else:
            data = content.read()
        content_type = getattr(content, 'content_type', None) or mimetypes.guess_type(name)[0] or 'application/octet-stream'
        with transaction.atomic():
            StoredMediaFile.objects.update_or_create(
                name=name,
                defaults={
                    'content': data,
                    'content_type': content_type,
                    'size': len(data),
                },
            )
        return name

    def delete(self, name):
        self._get_model().objects.filter(name=name).delete()

    def exists(self, name):
        return self._get_model().objects.filter(name=name).exists()

    def listdir(self, path):
        StoredMediaFile = self._get_model()
        prefix = path.rstrip('/') + '/' if path else ''
        names = StoredMediaFile.objects.filter(name__startswith=prefix).values_list('name', flat=True)
        dirs, files = set(), []
        for name in names:
            rest = name[len(prefix):] if prefix else name
            if '/' in rest:
                dirs.add(rest.split('/', 1)[0])
            elif rest:
                files.append(rest)
        return list(dirs), files

    def size(self, name):
        obj = self._get_model().objects.filter(name=name).only('size').first()
        if not obj:
            raise FileNotFoundError(name)
        return obj.size

    def url(self, name):
        from django.urls import reverse
        # reverse com path: usa kwargs
        return reverse('media_db_serve', kwargs={'name': name})

    def get_accessed_time(self, name):
        raise NotImplementedError

    def get_created_time(self, name):
        obj = self._get_model().objects.filter(name=name).only('criado_em').first()
        if not obj:
            raise FileNotFoundError(name)
        return obj.criado_em

    def get_modified_time(self, name):
        return self.get_created_time(name)
