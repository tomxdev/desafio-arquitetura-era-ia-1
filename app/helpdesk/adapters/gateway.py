from collections.abc import Iterator

import httpx2  # cliente HTTP do SDK openai 3.x (falhas no meio do stream chegam cruas)
from openai import APIConnectionError, APIError, APIStatusError, APITimeoutError, OpenAI

from ..ports import CapabilityUnavailable, LLMGateway


class GatewayClient(LLMGateway):
    """Único componente que fala com o modelo: cliente do AI Gateway (API compatível com OpenAI).

    A capacidade lógica vai como `model`; o gateway decide provider e modelo físico, e é ele quem
    faz retry e fallback (ADR 0009). Aqui: sem retries no SDK (`max_retries=0`), timeout explícito
    por capacidade e tradução das falhas do gateway para `CapabilityUnavailable`.
    """

    def __init__(self, base_url: str, api_key: str, timeouts: dict[str, float], default_timeout: float,
                 max_tokens: int) -> None:
        self._client = OpenAI(base_url=base_url, api_key=api_key, timeout=default_timeout, max_retries=0)
        self._timeouts = timeouts
        self._max_tokens = max_tokens

    def complete(self, capability: str, task: str, content: str) -> str:
        with _translated_errors(capability):
            response = self._create(capability, task, content, stream=False)
        return response.choices[0].message.content

    def stream(self, capability: str, task: str, content: str) -> Iterator[str]:
        # A requisição sai aqui: uma falha antes do 1º trecho (inclusive depois do fallback do gateway)
        # levanta já na chamada, e a rota ainda pode responder com status de erro.
        with _translated_errors(capability):
            chunks = self._create(capability, task, content, stream=True)
        return _text(capability, chunks)

    def _create(self, capability: str, task: str, content: str, stream: bool):
        client = self._client.with_options(timeout=self._timeouts.get(capability, self._client.timeout))
        return client.chat.completions.create(
            model=capability,
            max_tokens=self._max_tokens,
            messages=[{"role": "user", "content": f"TASK: {task}\n{content}"}],
            stream=stream,
        )


def _text(capability: str, chunks) -> Iterator[str]:
    # Falha no meio do stream: o gateway envia um evento de erro (o SDK levanta APIError) ou a
    # conexão cai/expira (httpx2). Nos dois casos, o texto parcial já foi entregue.
    with _translated_errors(capability, interrupted=True):
        for chunk in chunks:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class _translated_errors:
    def __init__(self, capability: str, interrupted: bool = False) -> None:
        self._capability = capability
        self._interrupted = interrupted

    def __enter__(self) -> None:
        return None

    def __exit__(self, kind, error, traceback) -> bool:
        if error is None or isinstance(error, (GeneratorExit, CapabilityUnavailable)):
            return False
        if isinstance(error, APITimeoutError) or isinstance(error, httpx2.TimeoutException):
            reason = "tempo esgotado esperando o gateway"
        elif isinstance(error, APIConnectionError) or isinstance(error, httpx2.TransportError):
            reason = "gateway inacessível"
        elif isinstance(error, APIStatusError):
            reason = ("orçamento ou limite de requisições da chave excedido" if error.status_code == 429
                      else f"nenhum modelo disponível (gateway respondeu {error.status_code})")
        elif isinstance(error, APIError):
            reason = "o gateway informou uma falha"
        else:
            return False
        if self._interrupted:
            reason = f"geração interrompida: {reason}"
        raise CapabilityUnavailable(self._capability, reason) from error
