from __future__ import annotations


class ProviderUnavailable(RuntimeError):
    pass


class AnthropicGateway:
    """One explicit provider path; retries reuse compiled prompt bytes."""

    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def complete(self, prompt: bytes) -> str:
        if not self.api_key:
            raise ProviderUnavailable("ANTHROPIC_API_KEY is not configured")
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.api_key)
            response = client.messages.create(model=self.model, max_tokens=4000, messages=[{"role": "user", "content": prompt.decode("utf-8")}])
            return "".join(block.text for block in response.content if hasattr(block, "text"))
        except Exception as exc:
            raise ProviderUnavailable("Anthropic provider request failed") from exc
