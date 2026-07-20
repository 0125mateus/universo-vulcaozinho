"""Assistente de IA do App do Hóspede (Recrear).

Responde dúvidas do hóspede usando o contexto real do dia (faixa, programação,
passeios, noite temática e passaporte). Usa OpenAI quando configurado; caso
contrário, cai em respostas guiadas locais.
"""

import re
from typing import Any

from django.conf import settings
from django.utils import timezone


def _dia_semana_hoje():
    return (timezone.localdate().weekday() + 1) % 7


def montar_contexto(hospede) -> str:
    """Monta um resumo textual do dia do hóspede para alimentar a IA."""
    from .models import InscricaoPasseio, NoiteTematica, Passeio, ProgramacaoDiaria

    hoje = timezone.localdate()
    hotel = hospede.hotel
    cat = hospede.categoria_recreacao

    linhas = [
        f'Hóspede: {hospede.nome_completo} (apartamento {hospede.apartamento}).',
        f'Hotel: {hotel.nome}, em {hotel.cidade}.',
        f'Faixa de recreação: {cat.nome if cat else "não definida"}.',
        f'Data de hoje: {hoje.strftime("%d/%m/%Y")}.',
    ]

    progs = (
        ProgramacaoDiaria.objects.filter(hotel=hotel, data=hoje)
        .select_related('atividade', 'local', 'categoria')
        .order_by('hora_inicio')
    )
    if cat:
        progs_faixa = progs.filter(categoria=cat)
    else:
        progs_faixa = progs
    if progs_faixa:
        linhas.append('Atividades de hoje da sua faixa:')
        for p in progs_faixa[:20]:
            linhas.append(
                f'- {p.hora_inicio:%H:%M} a {p.hora_fim:%H:%M}: {p.atividade.nome} '
                f'({p.local.nome})'
            )
    else:
        linhas.append('Não há atividades cadastradas para a sua faixa hoje.')

    passeios = Passeio.objects.filter(
        hotel=hotel, dia_semana=_dia_semana_hoje(), ativo=True,
    ).order_by('ordem', 'titulo')
    if passeios:
        linhas.append('Passeios de hoje:')
        for p in passeios:
            preco = 'incluso' if p.is_gratuito else f'R$ {p.preco}'
            saida = f', saída {p.hora_saida:%H:%M}' if p.hora_saida else ''
            linhas.append(f'- {p.titulo} ({preco}{saida}). {p.descricao}')
    else:
        linhas.append('Não há passeios cadastrados para hoje.')

    minhas_inscricoes = (
        InscricaoPasseio.objects.filter(hospede=hospede, data=hoje)
        .select_related('passeio')
    )
    if minhas_inscricoes:
        linhas.append('Suas inscrições em passeios hoje:')
        for insc in minhas_inscricoes:
            linhas.append(
                f'- {insc.passeio.titulo}: {insc.get_status_pagamento_display()}'
            )

    noite = NoiteTematica.objects.filter(hotel=hotel, dia_semana=_dia_semana_hoje()).first()
    if noite:
        linhas.append(
            f'Noite temática de hoje: {noite.tema}. '
            f'Vista-se: {noite.vista_se or "livre"}. '
            f'Música: {noite.atracao_musical}. '
            f'Gastronomia: {noite.descricao_gastronomia}.'
        )

    passaporte = getattr(hospede, 'passaporte', None)
    if passaporte:
        linhas.append(
            f'Passaporte: {passaporte.moedas} moedas, nível {passaporte.nivel}.'
        )

    return '\n'.join(linhas)


def _system_prompt(hospede) -> str:
    contexto = montar_contexto(hospede)
    return (
        'Você é o assistente **Recrear**, simpático e profissional do app do hóspede de um '
        'hotel de recreação. Fale em português do Brasil, de forma calorosa, curta e '
        'objetiva, como um recreador animado. Use os DADOS DE HOJE abaixo para responder. '
        'Ajude o hóspede com: programação de atividades, passeios (inclusive como pagar '
        'via PIX no app e enviar o comprovante), noite temática, passaporte e informações '
        'do hotel. Se a resposta não estiver nos dados, oriente o hóspede a procurar a '
        'recepção. Nunca invente horários, preços ou passeios que não estejam nos dados.\n\n'
        f'### DADOS DE HOJE\n{contexto}\n'
    )


def saudacao(hospede) -> str:
    nome = hospede.nome_completo.split()[0] if hospede.nome_completo else 'hóspede'
    return (
        f'Oi, {nome}! ✨ Sou a Recrear, sua guia aqui no app. '
        'Posso te contar a programação de hoje, os passeios, como pagar via PIX, '
        'a noite temática e seu passaporte. O que você quer saber?'
    )


def sugestoes() -> list[str]:
    return [
        'Qual a programação de hoje?',
        'Quais passeios têm hoje?',
        'Como pago o passeio pelo PIX?',
        'Qual a noite temática de hoje?',
        'Quantas moedas eu tenho?',
    ]


def _fallback(message: str, hospede) -> dict[str, Any]:
    from .models import InscricaoPasseio, NoiteTematica, Passeio, ProgramacaoDiaria

    texto = message.lower()
    hoje = timezone.localdate()
    hotel = hospede.hotel
    cat = hospede.categoria_recreacao

    if re.search(r'passeio|pix|paga|comprovante', texto):
        passeios = Passeio.objects.filter(
            hotel=hotel, dia_semana=_dia_semana_hoje(), ativo=True,
        ).order_by('ordem')
        if not passeios:
            return {'reply': 'Hoje não há passeios cadastrados. Confira amanhã ou pergunte na recepção!', 'source': 'guided'}
        linhas = ['🌴 **Passeios de hoje:**']
        for p in passeios:
            preco = 'incluso' if p.is_gratuito else f'R$ {p.preco}'
            linhas.append(f'• {p.titulo} — {preco}')
        linhas.append('\nPara pagar: abra o passeio, toque em **Pagar via PIX**, use o QR ou a chave copia-e-cola e envie o comprovante. A recepção confirma em seguida.')
        return {'reply': '\n'.join(linhas), 'source': 'guided'}

    if re.search(r'program|atividade|hor[áa]rio|agora', texto):
        progs = ProgramacaoDiaria.objects.filter(hotel=hotel, data=hoje)
        if cat:
            progs = progs.filter(categoria=cat)
        progs = progs.select_related('atividade', 'local').order_by('hora_inicio')
        if not progs:
            return {'reply': 'Não encontrei atividades da sua faixa hoje. Veja a aba **Programação** ou pergunte na recepção.', 'source': 'guided'}
        linhas = ['📅 **Sua programação de hoje:**']
        for p in progs[:12]:
            linhas.append(f'• {p.hora_inicio:%H:%M} — {p.atividade.nome} ({p.local.nome})')
        return {'reply': '\n'.join(linhas), 'source': 'guided'}

    if re.search(r'noite|tem[áa]tic|vista|festa|m[úu]sica', texto):
        noite = NoiteTematica.objects.filter(hotel=hotel, dia_semana=_dia_semana_hoje()).first()
        if not noite:
            return {'reply': 'Ainda não há noite temática cadastrada para hoje. 🌙', 'source': 'guided'}
        return {'reply': (
            f'🌙 **Noite de hoje: {noite.tema}**\n'
            f'• Vista-se: {noite.vista_se or "livre"}\n'
            f'• Música: {noite.atracao_musical}\n'
            f'• Gastronomia: {noite.descricao_gastronomia}'
        ), 'source': 'guided'}

    if re.search(r'passaporte|moeda|carimbo|n[íi]vel', texto):
        passaporte = getattr(hospede, 'passaporte', None)
        if not passaporte:
            return {'reply': 'Participe das noites temáticas para ganhar carimbos e moedas no seu **Passaporte**! 🛂', 'source': 'guided'}
        return {'reply': f'🛂 Seu passaporte: **{passaporte.moedas} moedas**, nível **{passaporte.nivel}**. Continue participando!', 'source': 'guided'}

    return {'reply': saudacao(hospede), 'source': 'guided'}


def chat(message: str, history: list[dict] | None, hospede) -> dict[str, Any]:
    message = (message or '').strip()
    if not message:
        return {'error': 'Digite uma mensagem.', 'reply': '', 'source': 'error'}

    history = history or []

    if settings.OPENAI_API_KEY:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            mensagens = [{'role': 'system', 'content': _system_prompt(hospede)}]
            for item in history[-8:]:
                role = item.get('role', 'user')
                if role in ('user', 'assistant'):
                    mensagens.append({'role': role, 'content': item.get('content', '')})
            mensagens.append({'role': 'user', 'content': message})

            resp = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=mensagens,
                temperature=0.5,
                max_tokens=600,
            )
            reply = resp.choices[0].message.content.strip()
            _registrar(hospede, message, reply, 'ai')
            return {'reply': reply, 'source': 'ai'}
        except Exception:
            result = _fallback(message, hospede)
            _registrar(hospede, message, result['reply'], result.get('source', 'guided'))
            return result

    result = _fallback(message, hospede)
    _registrar(hospede, message, result['reply'], result.get('source', 'guided'))
    return result


def _registrar(hospede, mensagem, resposta, fonte):
    from core.intelligence.learning import registrar_consulta
    registrar_consulta(
        hotel=hospede.hotel,
        usuario=None,
        canal='guest',
        mensagem=mensagem,
        resposta=resposta,
        fonte=fonte,
    )
