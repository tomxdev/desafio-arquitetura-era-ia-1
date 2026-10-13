from openai import OpenAI

from ..ports import LLMGateway


class GatewayClient(LLMGateway):
    """Único componente que fala com o modelo: cliente do AI Gateway (API compatível com OpenAI).

    A capacidade lógica vai como `model`; o gateway decide provider e modelo físico. Sem retries no
    SDK (`max_retries=0`) e com timeout explícito: resiliência não é decisão deste cliente.
    """

    def __init__(self, base_url: str, api_key: str, timeout: float, max_tokens: int) -> None:
        self._client = OpenAI(base_url=base_url, api_key=api_key, timeout=timeout, max_retries=0)
        self._max_tokens = max_tokens

    def complete(self, capability: str, task: str, content: str) -> str:
        response = self._client.chat.completions.create(
            model=capability,
            max_tokens=self._max_tokens,
            messages=[{"role": "user", "content": f"TASK: {task}\n{content}"}],
        )
        return response.choices[0].message.content
