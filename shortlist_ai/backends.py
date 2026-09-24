"""LLM backends behind one interface: send a system prompt + content, get back an
instance of a Pydantic model.

- ClaudeBackend: Anthropic API with structured outputs. Reads PDFs as pages, so
  scanned and multi-column resumes work.
- LocalBackend: an MLX model on Apple Silicon with schema-constrained decoding
  (Outlines). Nothing leaves the machine. Text only.
"""

import json
from functools import lru_cache
from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

CLAUDE_MODEL = "claude-opus-5"
LOCAL_MODEL = "mlx-community/Qwen3.5-9B-MLX-4bit"

# USD per million tokens (input, output), for cost reporting.
PRICES = {CLAUDE_MODEL: (5.00, 25.00)}


class BackendError(RuntimeError):
    pass


class Backend(Protocol):
    name: str
    model: str
    reads_documents: bool  # can take PDF document blocks, not just text

    def structured(self, system: str, content: list[dict], output_type: type[T]) -> T: ...


class Usage:
    """Accumulates token usage across calls for a cost estimate."""

    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0
        self.calls = 0

    def add(self, input_tokens: int, output_tokens: int):
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.calls += 1

    def cost_usd(self, model: str) -> float:
        if model not in PRICES:
            return 0.0
        price_in, price_out = PRICES[model]
        return (self.input_tokens * price_in + self.output_tokens * price_out) / 1e6


class ClaudeBackend:
    name = "claude"
    reads_documents = True

    def __init__(self, model: str = CLAUDE_MODEL, effort: str = "medium", client=None):
        import anthropic

        self.model = model
        self.effort = effort
        self.client = client or anthropic.Anthropic()
        self.usage = Usage()

    def structured(self, system: str, content: list[dict], output_type: type[T]) -> T:
        response = self.client.beta.messages.parse(
            model=self.model,
            max_tokens=16000,
            system=system,
            messages=[{"role": "user", "content": content}],
            output_format=output_type,
            thinking={"type": "adaptive"},
            output_config={"effort": self.effort},
            # If a safety classifier declines, retry server-side on Anthropic's
            # recommended fallback model instead of failing.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        if response.stop_reason == "refusal":
            raise BackendError(f"Claude declined the request (request {response._request_id})")
        if response.stop_reason == "max_tokens":
            raise BackendError(f"Output truncated at max_tokens (request {response._request_id})")
        self.usage.add(response.usage.input_tokens, response.usage.output_tokens)
        return response.parsed_output


class LocalBackend:
    name = "local"
    reads_documents = False

    def __init__(self, model: str = LOCAL_MODEL, max_tokens: int = 4096):
        self.model = model
        self.max_tokens = max_tokens
        self.usage = Usage()

    def structured(self, system: str, content: list[dict], output_type: type[T]) -> T:
        from outlines.inputs import Chat

        text = "\n\n".join(block["text"] for block in content if block["type"] == "text")
        if not text.strip():
            raise BackendError("The local backend needs text; this document has none (scanned PDF?).")
        # Small models follow field descriptions better when they can see them;
        # the decoder separately guarantees the output matches the schema.
        schema = json.dumps(output_type.model_json_schema())
        prompt = Chat([
            {"role": "system", "content": f"{system}\n\nOutput JSON matching this schema:\n{schema}"},
            {"role": "user", "content": text},
        ])
        raw = _load_local_generator(self.model)(prompt, output_type, max_tokens=self.max_tokens)
        try:
            return output_type.model_validate_json(raw)
        except ValueError as e:
            raise BackendError(f"Local model output didn't validate (likely truncated): {e}") from e


@lru_cache(maxsize=1)
def _load_local_generator(model_name: str):
    """Loading takes far longer than one generation, so do it once per process."""
    try:
        import mlx_lm
        import outlines
    except ImportError as e:
        raise BackendError("The local backend needs extras: pip install 'shortlist-ai[local]'") from e

    model, tokenizer = mlx_lm.load(model_name)
    # Qwen-style templates open a <think> block by default, which fights the JSON
    # constraint. Templates that don't use this variable ignore it.
    if tokenizer.chat_template:
        tokenizer.chat_template = "{%- set enable_thinking = false %}" + tokenizer.chat_template
    return outlines.from_mlxlm(model, tokenizer)


def get_backend(name: str, model: str | None = None) -> Backend:
    if name == "claude":
        return ClaudeBackend(model or CLAUDE_MODEL)
    if name == "local":
        return LocalBackend(model or LOCAL_MODEL)
    raise ValueError(f"Unknown backend: {name}")
