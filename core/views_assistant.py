import json

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from core.auth_utils import resolver_hotel_atual
from core.intelligence import chat_inteligente, init_assistente


@require_GET
def assistant_init(request):
    hotel = resolver_hotel_atual(request)
    if request.user.is_authenticated:
        data = init_assistente(hotel, request.user)
    else:
        from core.assistant_service import get_assistant_greeting, get_suggested_questions
        data = {
            'greeting': get_assistant_greeting(),
            'suggestions': get_suggested_questions(),
            'insights': [],
            'ai_enabled': bool(settings.OPENAI_API_KEY),
            'modo': 'Orientação',
        }
    return JsonResponse(data)


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

    hotel = resolver_hotel_atual(request)
    if request.user.is_authenticated:
        result = chat_inteligente(message, history, hotel=hotel, usuario=request.user)
    else:
        from core.assistant_service import chat as assistant_chat
        result = assistant_chat(message, history)

    if result.get('error') and not result.get('reply'):
        return JsonResponse(result, status=400)
    return JsonResponse(result)
