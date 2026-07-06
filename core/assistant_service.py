"""
Assistente Vulcãozinho — orientação do sistema de recreação multi-hotel.
Usa IA generativa quando OPENAI_API_KEY está configurada; caso contrário, respostas guiadas.
"""

import re
from typing import Any

from django.conf import settings

SYSTEM_KNOWLEDGE = """
Você é o **Vulcãozinho**, mascote e assistente oficial do sistema **Universo Vulcãozinho Inn**.
Seu tom é acolhedor, animado e profissional — como um recreador que ajuda a equipe e hóspedes.
Responda sempre em português do Brasil. Nunca invente funcionalidades que não existem.

## O que é o sistema
Sistema de recreação multi-hotel para a rede em Poços de Caldas/MG:
- **Nacional Inn** (tema verde)
- **Euro Suite** (tema vinho/laranja)
- **Dan Inn** (tema azul)

Hotéis são trocados no **seletor no topo** da página (canto superior direito).

## Menu principal (navegação)
- **Início** (`/`) — Dashboard com hóspedes ativos, noite temática do dia, faixas etárias e próximas atividades.
- **Faixas (Ages)** (`/faixas/`) — As 4 faixas etárias da recreação com contagem de hóspedes.
- **Programação** (`/programacao/`) — Grade diária de atividades por faixa etária.
- **Noites & Manhãs** (`/noites/`) — Calendário semanal de noites e manhãs temáticas.
- **Universo** (`/universo/`) — Infográfico completo da recreação.
- **Loja** (`/loja/`) — Produtos oficiais Vulcãozinho (acessórios e bonés temáticos).
- **Passaporte** (`/passaporte/`) — Passaporte da Diversão (7 carimbos das noites temáticas).
- **Reunião** (`/reuniao/`) — Sala de reunião em tempo real para diretores (vídeo + chat). Acesso: staff/gestores.
- **Admin** (`/admin/`) — Cadastros: hóspedes, atividades, programação, noites, loja, etc.

## Faixas etárias (Ages) — IMPORTANTE
| Faixa | Idade | Cor |
|-------|-------|-----|
| Vulcão Kids | 7–12 anos | Laranja |
| Boys & Girls | 13–17 anos | Azul |
| Adultos | 18–59 anos | Verde |
| Melhor Idade | 60+ anos | Roxo |

A idade do hóspede é calculada automaticamente pela data de nascimento no check-in.

## Horários fixos da recreação
- 10:00 — Início / Boas-vindas
- 13:00 — Intervalo Almoço
- 14:00 — Retorno às atividades
- 17:00 — Hora do Lanche
- 17:30 — Retorno
- 21:55 — Encerramento

## Noites temáticas (semana)
- Segunda: Cores (MPB)
- Terça: Black Night
- Quarta: Golden Night
- Quinta: Brasilidades (Noite Livre)
- Sexta: Moda de Viola (Sertanejo)
- Sábado: Festa Neon
- Domingo: White Family

## Passaporte da Diversão
Hóspedes coletam **7 carimbos** (um por noite temática). Ao completar, ganham presente especial.
Carimbos são registrados no admin ou futuro módulo de recepção.

## Admin — tarefas comuns
1. **Cadastrar hóspede**: Admin → Hóspedes → Adicionar (nome, nascimento, documento, apartamento, check-in).
2. **Programar atividade**: Admin → Programações diárias → escolher hotel, data, horário, atividade, faixa etária e local.
3. **Noites temáticas**: já vêm do seed; editar em Admin → Noites temáticas.
4. **Seeds úteis** (terminal):
   - `python manage.py seed_hoteis`
   - `python manage.py seed_categorias`
   - `python manage.py seed_noites_tematicas`
   - `python manage.py seed_programacao`
   - `python manage.py seed_loja`

## Módulos em desenvolvimento (não invente como prontos)
- Moedas Vulcãozinho e níveis Bronze/Ouro/Diamante
- Telão para TV
- App do hóspede
- Módulo completo de recepção (check-in rápido na interface)

Se perguntarem sobre isso, diga que está planejado e oriente ao admin ou à equipe.

## Problemas comuns
- **Sem atividades hoje**: rode `seed_programacao` ou cadastre no admin.
- **Sem hotéis**: rode `seed_hoteis`.
- **Faixas vazias**: rode `seed_categorias`.
- **Trocar hotel**: use o dropdown no topo da página.

Use listas e passos numerados quando explicar procedimentos. Seja breve mas completo.
"""

FALLBACK_RESPONSES = [
    (
        r'como (começar|usar|funciona)|primeiros passos|por onde',
        'Olá! Sou o **Vulcãozinho**! Para começar:\n\n'
        '1. Escolha o **hotel** no seletor do topo\n'
        '2. Veja o **Início** para o resumo do dia\n'
        '3. Confira **Faixas (Ages)** e **Programação**\n'
        '4. Use o **Admin** para cadastrar hóspedes e atividades\n\n'
        'Pergunte sobre qualquer tela que eu explico!',
    ),
    (
        r'faixa|ages|idade|vulcão kids|boys|melhor idade|adultos',
        'As **4 faixas etárias (Ages)** da recreação:\n\n'
        '• **Vulcão Kids** — 7 a 12 anos (laranja)\n'
        '• **Boys & Girls** — 13 a 17 anos (azul)\n'
        '• **Adultos** — 18 a 59 anos (verde)\n'
        '• **Melhor Idade** — 60+ anos (roxo)\n\n'
        'Acesse **Faixas (Ages)** no menu ou veja a grade em **Programação**.',
    ),
    (
        r'programação|programacao|atividade|grade|horário|horario',
        'A **Programação** mostra a grade do dia por faixa etária.\n\n'
        'Horários fixos: 10h início, 13h almoço, 14h retorno, 17h lanche, 21h55 encerramento.\n\n'
        'Para cadastrar: **Admin → Programações diárias → Adicionar**.\n'
        'Ou rode: `python manage.py seed_programacao`',
    ),
    (
        r'noite|temática|tematica|manhã|manha|vista-se|vista se',
        'As **Noites & Manhãs Temáticas** estão em `/noites/`.\n\n'
        'Cada dia da semana tem tema, música, vista-se e gastronomia.\n'
        'Ex.: Segunda = Cores, Terça = Black Night, Sábado = Festa Neon.\n\n'
        'Dados oficiais da rede — editáveis no Admin.',
    ),
    (
        r'passaporte|carimbo|carimbos|7 carimbos',
        'O **Passaporte da Diversão** (`/passaporte/`) rastreia os **7 carimbos** '
        'das noites temáticas por hóspede.\n\n'
        'Complete os 7 para ganhar presente especial do Vulcãozinho Inn!\n'
        'Carimbos são registrados no Admin → Passaportes dos hóspedes.',
    ),
    (
        r'loja|produto|boné|bone|acessório|acessorio',
        'A **Loja Oficial** (`/loja/`) lista acessórios e bonés das noites temáticas.\n\n'
        'Produtos cadastrados via Admin ou `python manage.py seed_loja`.',
    ),
    (
        r'hotel|nacional|euro|dan inn|trocar|selecionar',
        'Use o **seletor de hotel** no canto superior direito para alternar entre:\n\n'
        '• Nacional Inn (verde)\n• Euro Suite (vinho/laranja)\n• Dan Inn (azul)\n\n'
        'Cada hotel tem programação e hóspedes próprios.',
    ),
    (
        r'admin|cadastrar|hóspede|hospede|check-in|checkin',
        'Para **cadastrar hóspede**:\n\n'
        '1. Acesse `/admin/`\n'
        '2. **Hóspedes → Adicionar hóspede**\n'
        '3. Preencha nome, data nascimento, documento, apartamento e datas\n\n'
        'A faixa etária é calculada automaticamente pela idade.',
    ),
    (
        r'universo|infográfico|infografico|mapa',
        'A página **Universo** (`/universo/`) mostra o infográfico completo da recreação: '
        'missão, faixas, programação, passaporte, loja e roadmap do sistema.',
    ),
    (
        r'reunião|reuniao|diretor|videoconfer|sala de reuni',
        'A aba **Reunião** (`/reuniao/`) é a sala virtual para diretores:\n\n'
        '• **Videoconferência** ao vivo (Jitsi Meet — câmera e microfone)\n'
        '• **Chat em tempo real** ao lado da vídeo\n'
        '• Salas: Rede geral + uma por hotel\n\n'
        'Acesso restrito a usuários **staff/diretoria**. Troque a sala no seletor do topo.',
    ),
    (
        r'seed|comando|terminal|migrate|popular',
        'Comandos úteis no terminal (pasta do projeto):\n\n'
        '• `python manage.py seed_hoteis` — 3 hotéis\n'
        '• `python manage.py seed_categorias` — faixas Ages\n'
        '• `python manage.py seed_noites_tematicas` — 7 noites\n'
        '• `python manage.py seed_programacao` — atividades exemplo\n'
        '• `python manage.py seed_loja` — produtos\n'
        '• `python manage.py runserver` — iniciar servidor',
    ),
]

DEFAULT_FALLBACK = (
    'Oi! Sou o **Vulcãozinho**, seu guia neste sistema! Posso ajudar com:\n\n'
    '• Como usar o sistema\n'
    '• Faixas etárias (Ages)\n'
    '• Programação e horários\n'
    '• Noites temáticas\n'
    '• Passaporte e Loja\n'
    '• Cadastros no Admin\n\n'
    'O que você gostaria de saber?'
)


def _fallback_reply(message: str) -> dict[str, Any]:
    text = message.lower().strip()
    for pattern, reply in FALLBACK_RESPONSES:
        if re.search(pattern, text):
            return {'reply': reply, 'source': 'guided'}
    return {'reply': DEFAULT_FALLBACK, 'source': 'guided'}


def _call_openai(message: str, history: list[dict]) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    messages = [{'role': 'system', 'content': SYSTEM_KNOWLEDGE}]
    for item in history[-10:]:
        role = item.get('role', 'user')
        if role in ('user', 'assistant'):
            messages.append({'role': role, 'content': item.get('content', '')})
    messages.append({'role': 'user', 'content': message})

    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
        temperature=0.5,
        max_tokens=900,
    )
    return response.choices[0].message.content.strip()


def get_assistant_greeting() -> str:
    if settings.OPENAI_API_KEY:
        mode = 'assistente com IA generativa'
    else:
        mode = 'assistente guiado'
    return (
        f'Olá! Sou o **Vulcãozinho** — seu {mode}! 🌋\n\n'
        'Estou aqui para ajudar você a navegar no sistema de recreação: '
        'faixas etárias, programação, noites temáticas, passaporte, loja e admin.\n\n'
        'Como posso ajudar?'
    )


def get_suggested_questions() -> list[str]:
    return [
        'Como começar a usar o sistema?',
        'Quais são as faixas etárias (Ages)?',
        'Como cadastrar um hóspede?',
        'Como ver a programação de hoje?',
        'O que é o Passaporte da Diversão?',
    ]


def chat(message: str, history: list[dict] | None = None) -> dict[str, Any]:
    message = (message or '').strip()
    if not message:
        return {'error': 'Digite uma mensagem.', 'reply': '', 'source': 'error'}

    history = history or []

    if settings.OPENAI_API_KEY:
        try:
            reply = _call_openai(message, history)
            return {'reply': reply, 'source': 'ai'}
        except Exception as exc:
            result = _fallback_reply(message)
            result['reply'] += (
                f'\n\n_(IA indisponível: {exc}. Resposta orientada local.)_'
            )
            return result

    return _fallback_reply(message)
