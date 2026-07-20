import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from core.auth_utils import resolver_hotel_atual
from core.intelligence import chat_inteligente, gerar_insights, init_assistente


@login_required
@require_GET
def intelligence_init(request):
    hotel = resolver_hotel_atual(request)
    data = init_assistente(hotel, request.user)
    return JsonResponse(data)


@login_required
@require_GET
def intelligence_insights(request):
    hotel = resolver_hotel_atual(request)
    return JsonResponse({'insights': gerar_insights(hotel)})


@login_required
@require_POST
def intelligence_chat(request):
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido.'}, status=400)

    message = payload.get('message', '')
    history = payload.get('history', [])
    if not isinstance(history, list):
        history = []

    hotel = resolver_hotel_atual(request)
    result = chat_inteligente(message, history, hotel=hotel, usuario=request.user)
    if result.get('error') and not result.get('reply'):
        return JsonResponse(result, status=400)
    return JsonResponse(result)
