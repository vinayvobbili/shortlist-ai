"""LLM backends behind one interface: send a system prompt + content, get back an
instance of a Pydantic model.

- ClaudeBackend: Anthropic API with structured outputs. Reads PDFs as pages, so
  scanned and multi-column resumes work.
- LocalBackend: one shared OpenAI-compatible model server on this machine (LOCAL_LLM_URL, default
  http://127.0.0.1:8010/v1; vllm-mlx, mlx_lm.server, LM Studio, ...) with schema-constrained decoding.
  Nothing leaves the machine. Text only. The server holds the only copy of the model and queues
  requests from every program, so this backend loads nothing itself.
- OpenAIBackend: a hosted OpenAI-compatible API (NVIDIA build, Gemini's OpenAI endpoint, Groq, ...) with a
  bearer key you pass in; built by the caller (it needs a url and key), not by get_backend. Text only.
- AgyBackend: Google's Antigravity CLI (`agy`) on your own subscription login, no API key. Text only.
  Each call starts the CLI in an empty temporary directory, sandboxed, so its tools find nothing.
"""

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zlib
from typing import Protocol, TypeVar
from urllib.parse import urlsplit

from pydantic import BaseModel

from .prompts import request_text

T = TypeVar("T", bound=BaseModel)

CLAUDE_MODEL = "claude-opus-5"
LOCAL_MODEL = "local-server"  # a label only: the server decides which model answers
LOCAL_URL = "http://127.0.0.1:8010/v1"
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


def _looping(raw: str, window: int = 4000) -> bool:
    """True when the output ends in the same stretch of text over and over: a model stuck in a
    loop, which more room won't fix. Repeated text compresses to almost nothing; ordinary JSON
    doesn't (about a third of its size)."""
    tail = raw[-window:]
    return len(tail) == window and len(zlib.compress(tail.encode())) < window * 0.1


def _loop_breaker() -> dict:
    """Sampling with some randomness, in place of always taking the likeliest token, which is
    what keeps a stuck model repeating."""
    return {"temperature": 0.5, "top_p": 0.95}


def _server_message(body: bytes) -> str:
    """The error text in a server's reply: OpenAI's {"error": {"message": ...}}, or a plain string."""
    text = body.decode("utf-8", "replace").strip()
    try:
        data = json.loads(text)
    except ValueError:
        return text[:300]
    err = data.get("error", data.get("detail", data)) if isinstance(data, dict) else data
    if isinstance(err, dict):
        err = err.get("message", err)
    return str(err)[:300]


class LocalBackend:
    """The shared local model server (OpenAI-compatible, at LOCAL_LLM_URL). It holds the one copy of the model
    and queues requests from every program, so a call may wait behind others: the read timeout is long
    (LOCAL_LLM_TIMEOUT seconds, default 900) while connecting gives up fast. `model` is accepted for callers that
    still pass one; the server decides which model answers."""
    name = "local"
    reads_documents = False
    CONNECT_TIMEOUT = 5.0

    def __init__(self, model: str = LOCAL_MODEL, max_tokens: int = 4096, timeout: float | None = None):
        self.model = LOCAL_MODEL
        self.max_tokens = max_tokens
        self.timeout = timeout if timeout is not None else float(os.environ.get("LOCAL_LLM_TIMEOUT") or 900)
        self.usage = Usage()

    @property
    def url(self) -> str:
        return (os.environ.get("LOCAL_LLM_URL") or LOCAL_URL).rstrip("/")

    # What the OpenAIBackend below changes: who is named in messages, the request's headers and model, and how an
    # HTTP error reads.
    @property
    def who(self) -> str:
        return f"The local model server at {self.url}"

    def _headers(self) -> dict:
        return {"Content-Type": "application/json"}

    def _model_field(self) -> str:
        return "local"  # the server ignores it and fills in whatever model it runs

    def _response_format(self, output_type) -> dict:
        return {"response_format": {"type": "json_schema", "json_schema": {
            "name": output_type.__name__, "schema": output_type.model_json_schema(), "strict": True}}}

    def _http_error(self, e: urllib.error.HTTPError) -> BackendError:
        return BackendError(f"{self.who} answered {e.code}: {_server_message(e.read())}")

    def _post(self, body: dict) -> dict:
        url = f"{self.url}/chat/completions"
        refused = (f"no local model server at {self.url} "
                   "(start an OpenAI-compatible server there, or set LOCAL_LLM_URL)")
        request = urllib.request.Request(url, json.dumps(body).encode(), self._headers())
        try:
            parts = urlsplit(url)
            # urlopen has one timeout for connecting and reading; probe the connection first so a missing server
            # fails in seconds while a queued request may take as long as it needs.
            port = parts.port or (443 if parts.scheme == "https" else 80)
            socket.create_connection((parts.hostname, port), self.CONNECT_TIMEOUT).close()
            with urllib.request.urlopen(request, timeout=self.timeout) as reply:
                return json.loads(reply.read())
        except urllib.error.HTTPError as e:
            raise self._http_error(e) from e
        except TimeoutError as e:
            raise BackendError(f"{self.who} didn't answer within {self.timeout:g}s (timed out)") from e
        except ConnectionRefusedError as e:
            raise BackendError(refused) from e
        except urllib.error.URLError as e:
            if isinstance(e.reason, ConnectionRefusedError):
                raise BackendError(refused) from e
            if isinstance(e.reason, TimeoutError):
                raise BackendError(f"{self.who} timed out") from e
            raise BackendError(f"Can't reach {self.who}: {e.reason}") from e
        except (OSError, ValueError) as e:
            raise BackendError(f"{self.who} failed: {e}") from e

    def _generate(self, messages: list[dict], output_type, budget: int, **options) -> tuple[str, str | None]:
        """One request: the reply's text and its finish_reason ("length" means it ran out of tokens)."""
        reply = self._post({
            "model": self._model_field(),
            "messages": messages,
            "max_tokens": budget,
            **self._response_format(output_type),
            **options,
        })
        try:
            choice = reply["choices"][0]
            text = choice["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as e:
            raise BackendError(f"{self.who} sent an unexpected reply: {str(reply)[:200]}") from e
        used = reply.get("usage") or {}
        self.usage.add(int(used.get("prompt_tokens") or 0), int(used.get("completion_tokens") or 0))
        return text, choice.get("finish_reason")

    def structured(self, system: str, content: list[dict], output_type: type[T]) -> T:
        text = request_text(content)
        if not text.strip():
            raise BackendError("The local backend needs text; this document has none (scanned PDF?).")
        # Small models follow field descriptions better when they can see them;
        # the server's decoder separately guarantees the output matches the schema.
        schema = json.dumps(output_type.model_json_schema())
        messages = [
            {"role": "system", "content": f"{system}\n\nOutput JSON matching this schema:\n{schema}"},
            {"role": "user", "content": text},
        ]
        # A long posting can need more output than the default allows; the decoder stops
        # mid-JSON when it runs out, so try again with room to spare before giving up. A model
        # stuck repeating itself would only repeat itself for longer, so it gets one try with
        # some randomness instead.
        budget = self.max_tokens
        options = {}
        while True:
            raw, finish = self._generate(messages, output_type, budget, **options)
            try:
                return output_type.model_validate_json(raw)
            except ValueError as e:
                looping = _looping(raw)
                if looping and not options:
                    _say("the model got stuck repeating itself; trying once more with some randomness")
                    options = _loop_breaker()
                    continue
                if looping or finish == "stop" or budget >= self.max_tokens * 4:
                    why = ("stuck repeating itself" if looping
                           else "not the expected JSON" if finish == "stop" else "likely truncated")
                    raise BackendError(f"Local model output didn't validate at {budget} tokens ({why}): {e}") from e
                budget *= 2


class OpenAIBackend(LocalBackend):
    """A hosted OpenAI-compatible API (NVIDIA build, Gemini's OpenAI endpoint, Groq, ...): the local backend's client
    and retries, with `Authorization: Bearer <api_key>`, the model named in each request, and errors that say which
    provider answered what: a refused key reads "refused the key", so a caller can tell a step that can't score
    (key, quota, rate limit, a 5xx) from a job it can't. The key goes in the header only, never into a message.
    response_format: "json_schema" (strict schema-constrained decoding), "json_object" (any JSON; the schema is in
    the prompt) or "none", for a provider that rejects the first."""
    name = "openai"
    CONNECT_TIMEOUT = 10.0

    def __init__(self, model: str, url: str, api_key: str, provider: str = "openai", max_tokens: int = 4096,
                 timeout: float | None = None, response_format: str = "json_schema"):
        if response_format not in ("json_schema", "json_object", "none"):
            raise ValueError(f"response_format is json_schema, json_object or none, got {response_format!r}")
        super().__init__(max_tokens=max_tokens, timeout=timeout if timeout is not None else 300.0)
        self.model = model
        self.base_url = url.rstrip("/")
        self.api_key = api_key
        self.provider = provider
        self.response_format = response_format

    @property
    def url(self) -> str:
        return self.base_url

    @property
    def who(self) -> str:
        return f"The {self.provider} API at {self.url}"

    def _headers(self) -> dict:
        return {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}

    def _model_field(self) -> str:
        return self.model

    def _response_format(self, output_type) -> dict:
        if self.response_format == "json_schema":
            return super()._response_format(output_type)
        return {"response_format": {"type": "json_object"}} if self.response_format == "json_object" else {}

    def _http_error(self, e: urllib.error.HTTPError) -> BackendError:
        said = _server_message(e.read())
        if e.code in (401, 403):
            return BackendError(f"{self.who} refused the key ({e.code}): {said}")
        return BackendError(f"{self.who} answered {e.code}: {said}")

    def _generate(self, messages: list[dict], output_type, budget: int, **options) -> tuple[str, str | None]:
        text, finish = super()._generate(messages, output_type, budget, **options)
        if not text.strip():
            raise BackendError(f"{self.who} ({self.model}) answered with nothing")
        return _first_json_object(text), finish  # a model may fence the JSON, or add a line after it


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
            # agy checks the answer against --json-schema itself: some models (Gemini) leave `response` empty and
            # give only that
            parsed = reply.get("structured_output")
            if not raw and not isinstance(parsed, dict):
                raise BackendError(f"agy ({self.model}) answered with nothing")
            try:
                result = (output_type.model_validate(parsed) if isinstance(parsed, dict)
                          else output_type.model_validate_json(_first_json_object(raw)))
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
