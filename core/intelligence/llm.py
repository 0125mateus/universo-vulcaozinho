"""Cliente OpenAI compartilhado."""

from django.conf import settings


def openai_disponivel() -> bool:
    return bool(getattr(settings, 'OPENAI_API_KEY', ''))


def chamar_openai(messages: list[dict], *, temperature: float = 0.45, max_tokens: int = 900) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()
