from dataclasses import dataclass
from typing import Optional

from django.conf import settings


@dataclass(frozen=True)
class AIChatSettings:
    api_key: Optional[str]
    model: str
    max_input_tokens: int
    max_output_tokens: int
    request_timeout: int


DEFAULT_AI_MODEL = getattr(settings, "OPENAI_DEFAULT_MODEL", "gpt-4-turbo")
DEFAULT_MAX_INPUT_TOKENS = getattr(settings, "OPENAI_MAX_TOKENS", 4096)
DEFAULT_MAX_OUTPUT_TOKENS = getattr(settings, "OPENAI_MAX_COMPLETION_TOKENS", 1024)
DEFAULT_REQUEST_TIMEOUT = getattr(settings, "OPENAI_REQUEST_TIMEOUT", 30)


def get_ai_chat_settings() -> AIChatSettings:
    """Retorna as configurações centralizadas para chamadas de chat com IA."""

    return AIChatSettings(
        api_key=getattr(settings, "OPENAI_API_KEY", None),
        model=DEFAULT_AI_MODEL,
        max_input_tokens=DEFAULT_MAX_INPUT_TOKENS,
        max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS,
        request_timeout=DEFAULT_REQUEST_TIMEOUT,
    )
