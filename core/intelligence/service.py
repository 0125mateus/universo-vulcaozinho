"""Assistente inteligente — contexto ao vivo + insights + aprendizado."""

from typing import Any

from django.contrib.auth.models import AnonymousUser

from core.assistant_service import SYSTEM_KNOWLEDGE, _fallback_reply

from .context import montar_contexto_hotel
from .insights import gerar_insights
from .learning import registrar_consulta, resumo_aprendizado, sugestoes_aprendidas
from .llm import chamar_openai, openai_disponivel


def _insights_texto(hotel) -> str:
    linhas = []
    for ins in gerar_insights(hotel):
        linhas.append(f"- [{ins['prioridade'].upper()}] {ins['titulo']}: {ins['descricao']}")
    return '\n'.join(linhas) if linhas else 'Nenhum alerta no momento.'


def _system_prompt(hotel, usuario) -> str:
    ctx = montar_contexto_hotel(hotel)
    alertas = _insights_texto(hotel)
    aprend = resumo_aprendizado(hotel)
    papel = ''
    if usuario and not isinstance(usuario, AnonymousUser) and usuario.is_authenticated:
        perfil = getattr(usuario, 'perfilusuario', None)
        if perfil:
            papel = f'Papel do usuário: {perfil.get_papel_display()}.'
    return (
        f'{SYSTEM_KNOWLEDGE}\n\n'
        '## Modo inteligente\n'
        'Você tem acesso a DADOS REAIS e ALERTAS do hotel abaixo. '
        'Use-os para responder com precisão. Nunca invente números ou atividades.\n'
        'Quando sugerir ações, indique rotas do sistema (/recepcao/, /dashboard/, etc.).\n'
        f'{papel}\n\n'
        f'### DADOS OPERACIONAIS DE HOJE\n{ctx}\n\n'
        f'### ALERTAS E INSIGHTS\n{alertas}\n\n'
        f'### APRENDIZADO\n{aprend or "Sem histórico de perguntas ainda."}\n'
    )


def init_assistente(hotel, usuario) -> dict[str, Any]:
    insights = gerar_insights(hotel)
    aprendidas = sugestoes_aprendidas(hotel)
    base = [
        'O que devo priorizar hoje?',
        'Como está a ocupação das atividades?',
        'Há pagamentos de passeio pendentes?',
        'Resumo operacional do hotel',
    ]
    sugestoes = aprendidas + [s for s in base if s not in aprendidas]
    modo = 'IA + dados ao vivo' if openai_disponivel() else 'Análise guiada + dados ao vivo'
    saudacao = (
        f'Olá! Sou a **Recrear Inteligente** — {modo}. ✨\n\n'
        'Analiso hóspedes, programação, passeios, loja e ponto do hotel em tempo real.\n'
    )
    if insights and insights[0].get('tipo') != 'info':
        saudacao += f'\n**Destaque:** {insights[0]["titulo"]} — {insights[0]["descricao"]}\n'
    saudacao += '\nComo posso ajudar?'
    return {
        'greeting': saudacao,
        'suggestions': sugestoes[:6],
        'insights': insights,
        'ai_enabled': openai_disponivel(),
        'modo': modo,
    }


def chat_inteligente(
    message: str,
    history: list[dict] | None,
    *,
    hotel=None,
    usuario=None,
) -> dict[str, Any]:
    message = (message or '').strip()
    if not message:
        return {'error': 'Digite uma mensagem.', 'reply': '', 'source': 'error'}

    history = history or []
    msg_lower = message.lower()

    # Respostas diretas sobre insights
    if any(k in msg_lower for k in ('insight', 'alerta', 'priorizar', 'prioridade', 'resumo operacional')):
        insights = gerar_insights(hotel)
        linhas = ['**Análise Recrear — prioridades de hoje:**\n']
        for ins in insights:
            emoji = {'alta': '🔴', 'media': '🟡', 'baixa': '🟢'}.get(ins['prioridade'], '•')
            linhas.append(f"{emoji} **{ins['titulo']}** — {ins['descricao']}")
        reply = '\n'.join(linhas)
        registrar_consulta(
            hotel=hotel, usuario=usuario, canal='staff',
            mensagem=message, resposta=reply, fonte='insights',
        )
        return {'reply': reply, 'source': 'insights', 'insights': insights}

    if openai_disponivel() and hotel:
        try:
            messages = [{'role': 'system', 'content': _system_prompt(hotel, usuario)}]
            for item in history[-10:]:
                role = item.get('role', 'user')
                if role in ('user', 'assistant'):
                    messages.append({'role': role, 'content': item.get('content', '')})
            messages.append({'role': 'user', 'content': message})
            reply = chamar_openai(messages)
            registrar_consulta(
                hotel=hotel, usuario=usuario, canal='staff',
                mensagem=message, resposta=reply, fonte='ai',
            )
            return {'reply': reply, 'source': 'ai', 'insights': gerar_insights(hotel)}
        except Exception as exc:
            result = _fallback_reply(message)
            result['reply'] += f'\n\n_(IA indisponível: {exc}. Resposta orientada local.)_'
            registrar_consulta(
                hotel=hotel, usuario=usuario, canal='staff',
                mensagem=message, resposta=result['reply'], fonte='guided',
            )
            return result

    # Fallback enriquecido com contexto
    result = _fallback_reply(message)
    if hotel:
        ctx = montar_contexto_hotel(hotel)
        if any(k in msg_lower for k in ('hoje', 'resumo', 'situação', 'situacao', 'quantos')):
            result['reply'] += f'\n\n**Dados de hoje:**\n```\n{ctx[:1200]}\n```'
        result['insights'] = gerar_insights(hotel)
    registrar_consulta(
        hotel=hotel, usuario=usuario, canal='staff',
        mensagem=message, resposta=result['reply'], fonte=result.get('source', 'guided'),
    )
    return result
