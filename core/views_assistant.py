import json

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from .assistant_service import chat as assistant_chat, get_assistant_greeting, get_suggested_questions


@require_GET
def assistant_init(request):
    return JsonResponse({
        'greeting': get_assistant_greeting(),
        'suggestions': get_suggested_questions(),
        'ai_enabled': bool(settings.OPENAI_API_KEY),
    })


@require_POST
def assistant_chat_view(request):
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido.'}, status=400)

    message = payload.get('message', '')
    history = payload.get('history', [])
    if not isinstance(history, list):
        history = []

    result = assistant_chat(message, history)
    if result.get('error') and not result.get('reply'):
        return JsonResponse(result, status=400)
    return JsonResponse(result)
