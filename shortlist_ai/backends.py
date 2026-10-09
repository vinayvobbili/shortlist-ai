"""LLM backends behind one interface: send a system prompt + content, get back an
instance of a Pydantic model.

- ClaudeBackend: Anthropic API with structured outputs. Reads PDFs as pages, so
  scanned and multi-column resumes work.
- LocalBackend: an MLX model on Apple Silicon with schema-constrained decoding
  (Outlines). Nothing leaves the machine. Text only. Processes using it take turns on the
  GPU (ModelLock), so two programs scoring at once don't run each other out of memory.
"""

import fcntl
import json
import os
import sys
import time
from collections.abc import Callable
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
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


def _say(msg: str):
    print(f"  {msg}", file=sys.stderr, flush=True)


class ModelLock:
    """One process at a time on the local model, across every program on this machine.

    An exclusive OS file lock (flock) taken for each call, not for the life of the process, so a
    long-running program that keeps its model loaded doesn't hold the GPU while idle. The holder
    writes its pid into the file, so a waiting process can say whom it waits for. The OS drops the
    lock when the holder exits, even if it crashes, so a dead process never blocks the next one.

    The file is ~/.cache/shortlist-ai/local-model.lock unless SHORTLIST_MODEL_LOCK names another.
    Waiting has no limit unless `timeout` (or SHORTLIST_MODEL_LOCK_TIMEOUT, in seconds) sets one."""

    POLL = 0.5

    def __init__(self, path: Path | None = None, timeout: float | None = None,
                 notify: Callable[[str], None] | None = None):
        self.path = Path(path or os.environ.get("SHORTLIST_MODEL_LOCK")
                         or Path.home() / ".cache" / "shortlist-ai" / "local-model.lock")
        env_timeout = os.environ.get("SHORTLIST_MODEL_LOCK_TIMEOUT")
        self.timeout = timeout if timeout is not None else (float(env_timeout) if env_timeout else None)
        self.notify = notify or _say

    def holder(self) -> str:
        try:
            return self.path.read_text().strip() or "unknown"
        except OSError:
            return "unknown"

    @contextmanager
    def held(self):
        """Wait for the lock, hold it for the `with` block, and always let it go afterwards. Each
        use opens the file afresh, so threads of one process also take turns."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a+") as f:  # closing the file drops the lock, whatever happens
            if not self._try(f):
                self.notify(f"waiting for another process using the local model (pid {self.holder()})")
                deadline = None if self.timeout is None else time.monotonic() + self.timeout
                while not self._try(f):
                    if deadline is not None and time.monotonic() >= deadline:
                        raise BackendError(f"Gave up after {self.timeout:g}s waiting for the local model "
                                           f"(held by pid {self.holder()}; lock file {self.path})")
                    time.sleep(self.POLL)
            try:
                f.seek(0)
                f.truncate()
                f.write(str(os.getpid()))
                f.flush()
                yield
            finally:
                f.seek(0)
                f.truncate()
                f.flush()
                fcntl.flock(f, fcntl.LOCK_UN)

    @staticmethod
    def _try(f) -> bool:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except BlockingIOError:
            return False


def _out_of_gpu_memory(e: BaseException) -> bool:
    return isinstance(e, RuntimeError) and "insufficient memory" in str(e).lower()


def _free_gpu_cache():
    try:
        import mlx.core as mx
    except ImportError:
        return
    clear = getattr(mx, "clear_cache", None) or getattr(getattr(mx, "metal", None), "clear_cache", None)
    if clear:
        clear()


class LocalBackend:
    name = "local"
    reads_documents = False
    OOM_PAUSE = 5.0  # seconds to wait before the one retry after the GPU ran out of memory

    def __init__(self, model: str = LOCAL_MODEL, max_tokens: int = 4096, lock: ModelLock | None = None):
        self.model = model
        self.max_tokens = max_tokens
        self.usage = Usage()
        self.lock = lock or ModelLock()

    def _generate(self, prompt, output_type, budget: int) -> str:
        """One generation, holding the GPU for its length (the first also loads the model). If the
        GPU still runs out of memory (something outside shortlist-ai is using it), free what MLX
        has cached and try once more before failing."""
        with self.lock.held():
            try:
                return _load_local_generator(self.model)(prompt, output_type, max_tokens=budget)
            except RuntimeError as e:
                if not _out_of_gpu_memory(e):
                    raise
                _say(f"the GPU ran out of memory; retrying once in {self.OOM_PAUSE:g}s")
                _free_gpu_cache()
                time.sleep(self.OOM_PAUSE)
                return _load_local_generator(self.model)(prompt, output_type, max_tokens=budget)

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
        # A long posting can need more output than the default allows; the decoder stops
        # mid-JSON when it runs out, so try again with room to spare before giving up.
        budget = self.max_tokens
        while True:
            raw = self._generate(prompt, output_type, budget)
            try:
                return output_type.model_validate_json(raw)
            except ValueError as e:
                if budget >= self.max_tokens * 4:
                    raise BackendError(f"Local model output didn't validate at {budget} tokens "
                                       f"(likely truncated): {e}") from e
                budget *= 2


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
