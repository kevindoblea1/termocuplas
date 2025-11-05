from __future__ import annotations

from django.conf import settings
from django.http import HttpResponse


class SimpleCorsMiddleware:
    """Middleware mínimo para habilitar CORS en desarrollo."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == 'OPTIONS':
            response = HttpResponse()
            return self._add_cors_headers(request, response)

        response = self.get_response(request)
        return self._add_cors_headers(request, response)

    def _add_cors_headers(self, request, response: HttpResponse) -> HttpResponse:
        allow_all = getattr(settings, 'CORS_ALLOW_ALL_ORIGINS', True)
        origin = request.headers.get('Origin')
        allow_origin = '*'
        if not allow_all:
            allowed_origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', [])
            allow_origin = origin if origin in allowed_origins else ''
        elif origin:
            allow_origin = origin
        response['Access-Control-Allow-Origin'] = allow_origin or '*'
        response['Access-Control-Allow-Credentials'] = (
            'true' if getattr(settings, 'CORS_ALLOW_CREDENTIALS', True) else 'false'
        )
        response.setdefault('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.setdefault('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS')
        return response
