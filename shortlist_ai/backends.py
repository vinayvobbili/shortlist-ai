"""LLM backends behind one interface: send a system prompt + content, get back an
instance of a Pydantic model.

- ClaudeBackend: Anthropic API with structured outputs. Reads PDFs as pages, so
  scanned and multi-column resumes work.
- LocalBackend: an MLX model on Apple Silicon with schema-constrained decoding
  (Outlines). Nothing leaves the machine. Text only. Processes using it take turns on the
  GPU (ModelLock), so two programs scoring at once don't run each other out of memory.
- AgyBackend: Google's Antigravity CLI (`agy`) on your own subscription login, no API key. Text only.
  Each call starts the CLI in an empty temporary directory, sandboxed, so its tools find nothing.
"""

import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zlib
from collections.abc import Callable
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Protocol, TypeVar

from pydantic import BaseModel

from .prompts import request_text

T = TypeVar("T", bound=BaseModel)

CLAUDE_MODEL = "claude-opus-5"
LOCAL_MODEL = "mlx-community/Qwen3.5-9B-MLX-4bit"
AGY_MODEL = "claude-sonnet-5-5-medium"  # `agy models` lists the ids

# USD per million tokens (input, output), for cost reporting.
PRICES = {CLAUDE_MODEL: (5.00, 25.00)}
# Prompt-cache writes and reads, as multiples of the input price (5-minute cache).
CACHE_WRITE, CACHE_READ = 1.25, 0.10


def cached_system(system: str) -> list[dict]:
    """The system prompt as one block marked for prompt caching: every call of a kind (job requirements, score,
    years check) shares it, so calls within 5 minutes of each other read it from the cache. A prompt shorter than
    the model's minimum just isn't cached. Caching doesn't change the answer, so it isn't part of any cache key."""
    return [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]


class BackendError(RuntimeError):
    pass


class Deferred(Exception):
    """A model call queued for the next batch (see batch.py): it has no answer yet."""


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
        self.cache_write_tokens = 0
        self.cache_read_tokens = 0
        self.calls = 0

    def add(self, input_tokens: int, output_tokens: int, cache_write_tokens: int = 0, cache_read_tokens: int = 0):
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.cache_write_tokens += cache_write_tokens
        self.cache_read_tokens += cache_read_tokens
        self.calls += 1

    def add_reply(self, usage):
        """A reply's usage (input_tokens leaves out what was written to or read from the prompt cache)."""
        self.add(usage.input_tokens, usage.output_tokens,
                 getattr(usage, "cache_creation_input_tokens", None) or 0,
                 getattr(usage, "cache_read_input_tokens", None) or 0)

    def cost_usd(self, model: str) -> float:
        if model not in PRICES:
            return 0.0
        price_in, price_out = PRICES[model]
        cached = self.cache_write_tokens * CACHE_WRITE + self.cache_read_tokens * CACHE_READ
        return ((self.input_tokens + cached) * price_in + self.output_tokens * price_out) / 1e6


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
            system=cached_system(system),
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
        self.usage.add_reply(response.usage)
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


def _looping(raw: str, window: int = 4000) -> bool:
    """True when the output ends in the same stretch of text over and over: a model stuck in a
    loop, which more room won't fix. Repeated text compresses to almost nothing; ordinary JSON
    doesn't (about a third of its size)."""
    tail = raw[-window:]
    return len(tail) == window and len(zlib.compress(tail.encode())) < window * 0.1


def _loop_breaker():
    """Sampling with some randomness, in place of always taking the likeliest token, which is
    what keeps a stuck model repeating."""
    from mlx_lm.sample_utils import make_sampler

    return make_sampler(temp=0.5, top_p=0.95)


class LocalBackend:
    name = "local"
    reads_documents = False
    OOM_PAUSE = 5.0  # seconds to wait before the one retry after the GPU ran out of memory

    def __init__(self, model: str = LOCAL_MODEL, max_tokens: int = 4096, lock: ModelLock | None = None):
        self.model = model
        self.max_tokens = max_tokens
        self.usage = Usage()
        self.lock = lock or ModelLock()

    def _generate(self, prompt, output_type, budget: int, **options) -> str:
        """One generation, holding the GPU for its length (the first also loads the model). If the
        GPU still runs out of memory (something outside shortlist-ai is using it), free what MLX
        has cached and try once more before failing."""
        with self.lock.held():
            try:
                return _load_local_generator(self.model)(prompt, output_type, max_tokens=budget, **options)
            except RuntimeError as e:
                if not _out_of_gpu_memory(e):
                    raise
                _say(f"the GPU ran out of memory; retrying once in {self.OOM_PAUSE:g}s")
                _free_gpu_cache()
                time.sleep(self.OOM_PAUSE)
                return _load_local_generator(self.model)(prompt, output_type, max_tokens=budget, **options)

    def structured(self, system: str, content: list[dict], output_type: type[T]) -> T:
        from outlines.inputs import Chat

        text = request_text(content)
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
        # mid-JSON when it runs out, so try again with room to spare before giving up. A model
        # stuck repeating itself would only repeat itself for longer, so it gets one try with
        # some randomness instead.
        budget = self.max_tokens
        options = {}
        while True:
            raw = self._generate(prompt, output_type, budget, **options)
            try:
                return output_type.model_validate_json(raw)
            except ValueError as e:
                looping = _looping(raw)
                if looping and not options:
                    _say("the model got stuck repeating itself; trying once more with some randomness")
                    options = {"sampler": _loop_breaker()}
                    continue
                if looping or budget >= self.max_tokens * 4:
                    why = "stuck repeating itself" if looping else "likely truncated"
                    raise BackendError(f"Local model output didn't validate at {budget} tokens ({why}): {e}") from e
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


QUOTA_WORDS = re.compile(r"quota|rate.?limit|usage limit|limit (reached|exceeded)|exhausted|too many requests|\b429\b",
                         re.IGNORECASE)


class AgyBackend:
    """Antigravity CLI: `agy -p PROMPT --output-format json --json-schema SCHEMA` run in an empty temporary
    directory with --sandbox. agy has no system-prompt option, so the system text opens the prompt. A failed
    call (agy missing, a timeout, a status other than SUCCESS, quota used up, an answer that isn't the schema)
    raises BackendError, so a caller with another backend to try can move on."""
    name = "agy"
    reads_documents = False
    executable = "agy"

    def __init__(self, model: str = AGY_MODEL, timeout: float = 180.0):
        self.model = model
        self.timeout = timeout  # seconds for one call; agy itself is told a little less
        self.usage = Usage()

    def _run(self, prompt: str, schema: str) -> dict:
        exe = shutil.which(self.executable)
        if not exe:
            raise BackendError("agy (Antigravity CLI) isn't installed or isn't on PATH")
        args = [exe, "-p", prompt, "--output-format", "json", "--model", self.model, "--sandbox",
                "--disable-slash-commands", "--json-schema", schema,
                "--print-timeout", f"{max(int(self.timeout) - 10, 10)}s"]
        with tempfile.TemporaryDirectory(prefix="agy-") as empty:
            try:
                done = subprocess.run(args, cwd=empty, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                                      timeout=self.timeout)
            except subprocess.TimeoutExpired:
                raise BackendError(f"agy didn't answer within {self.timeout:g}s") from None
            except OSError as e:
                raise BackendError(f"agy couldn't start: {e}") from e
        out = (done.stdout or "").strip()
        try:
            reply = json.loads(out)
        except ValueError:
            reply = None
        if done.returncode != 0 or not isinstance(reply, dict):
            detail = (done.stderr or out or "no output").strip()[:300]
            kind = "agy's quota or rate limit" if QUOTA_WORDS.search(detail) else "agy failed"
            raise BackendError(f"{kind} (exit {done.returncode}): {detail}")
        if reply.get("status") != "SUCCESS":
            detail = str(reply.get("response") or reply.get("error") or reply)[:300]
            kind = "agy's quota or rate limit" if QUOTA_WORDS.search(detail) else f"agy status {reply.get('status')}"
            raise BackendError(f"{kind}: {detail}")
        return reply

    def structured(self, system: str, content: list[dict], output_type: type[T]) -> T:
        text = request_text(content)
        if not text.strip():
            raise BackendError("The agy backend needs text; this document has none (scanned PDF?).")
        schema = json.dumps(output_type.model_json_schema())
        prompt = (f"{system}\n\nAnswer with one JSON object matching this schema, and nothing else:\n{schema}"
                  f"\n\n---\n\n{text}")
        for attempt in (1, 2):
            reply = self._run(prompt, schema)
            raw = str(reply.get("response") or "").strip()
            raw = _first_json_object(raw)
            try:
                result = output_type.model_validate_json(raw)
            except ValueError as e:
                raise BackendError(f"agy's answer didn't validate: {e}") from e
            used = reply.get("usage") or {}
            self.usage.add(int(used.get("input_tokens") or 0), int(used.get("output_tokens") or 0))
            if attempt == 2 or not _nothing_listed(result):
                return result
        return result  # pragma: no cover


def _first_json_object(raw: str) -> str:
    """The first JSON object in agy's answer: a model may fence it, or add a line of text after it."""
    start = raw.find("{")
    if start < 0:
        return raw
    try:
        _, end = json.JSONDecoder().raw_decode(raw, start)
    except ValueError:
        return raw
    return raw[start:end]


def _nothing_listed(result: BaseModel) -> bool:
    """Every list in the answer is empty (agy now and then answers a long posting with `{"requirements": []}`):
    worth one more try before the answer is believed and cached."""
    lists = [v for v in result.__dict__.values() if isinstance(v, list)]
    return bool(lists) and not any(lists)


def get_backend(name: str, model: str | None = None) -> Backend:
    if name == "claude":
        return ClaudeBackend(model or CLAUDE_MODEL)
    if name == "local":
        return LocalBackend(model or LOCAL_MODEL)
    if name == "agy":
        return AgyBackend(model or AGY_MODEL)
    raise ValueError(f"Unknown backend: {name}")
