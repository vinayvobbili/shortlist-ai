"""Claude through the Message Batches API, behind the same Backend interface: half the price, with results
within 24 hours (usually minutes), for runs nobody is waiting on.

The pipeline makes its model calls one after another (a job's requirements before its score, its score before
any years check), so a batch run goes in rounds. BatchBackend.run(work) calls work(); each model call without a
stored answer is queued, and fails for that round with Deferred (the pipeline records it as that job's error).
The queued calls go out as one batch, and when it ends work() runs again, its earlier calls now answered from
disk. It stops when a round queues nothing. Scoring a set of jobs takes a few rounds: requirements, then the
score, then one per "N+ years" check (score.py makes those in turn). Rounds cost waiting, not money.

Answers are kept on disk by request, and so is every batch still out, so a run stopped while one is processing
collects it next time instead of paying for the same calls twice."""

import hashlib
import json
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from .backends import CLAUDE_MODEL, BackendError, Deferred, Usage, _say, cached_system

__all__ = ["BatchBackend", "Deferred"]

T = TypeVar("T", bound=BaseModel)
R = TypeVar("R")


class BatchBackend:
    name = "claude"  # its answers mean what the Messages API's do, so the extraction cache is shared
    reads_documents = True

    def __init__(self, store: Path, model: str = CLAUDE_MODEL, effort: str = "medium", client=None,
                 poll: float = 30.0, notify: Callable[[str], None] | None = None):
        import anthropic

        self.model = model
        self.effort = effort
        self.client = client or anthropic.Anthropic()
        self.store = Path(store)
        self.poll = poll
        self.notify = notify or _say
        self.usage = Usage()
        self.pending: dict[str, dict] = {}   # this round's calls with no answer: request key -> params
        self.failed: dict[str, str] = {}     # calls the batch didn't answer, this run only: the next run retries
        self._lock = threading.Lock()

    def params(self, system: str, content: list[dict], output_type: type[BaseModel]) -> dict:
        """The Messages API request for one call, as ClaudeBackend makes it (less its server-side fallback)."""
        from anthropic import transform_schema

        return {"model": self.model, "max_tokens": 16000, "system": system,
                "messages": [{"role": "user", "content": content}],
                "thinking": {"type": "adaptive"},
                "output_config": {"effort": self.effort, "format": {
                    "type": "json_schema", "schema": transform_schema(output_type.model_json_schema())}}}

    def structured(self, system: str, content: list[dict], output_type: type[T]) -> T:
        params = self.params(system, content, output_type)
        key = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()[:40]
        if key in self.failed:
            raise BackendError(self.failed[key])
        path = self._answers / f"{key}.json"
        if not path.exists():
            with self._lock:
                self.pending[key] = params
            raise Deferred(key)
        return output_type.model_validate_json(json.loads(path.read_text())["text"])

    def run(self, work: Callable[[], R]) -> R:
        """work() in rounds, sending what each round queued as one batch, until a round queues nothing."""
        while True:
            self.pending.clear()
            try:
                result = work()
            except Deferred:  # a call every job waits on (the resume): no result this round
                result = None
            if not self.pending:
                return result
            self._send(dict(self.pending))

    @property
    def _answers(self) -> Path:
        return self.store / "answers"

    @property
    def _batches(self) -> Path:
        return self.store / "batches"

    def _out(self) -> dict[str, set[str]]:
        """Batches sent and not yet collected (by this run or one before it): batch id -> request keys."""
        if not self._batches.is_dir():
            return {}
        return {p.stem: set(json.loads(p.read_text())) for p in self._batches.glob("*.json")}

    def _send(self, pending: dict[str, dict]):
        out = self._out()
        waiting = {batch for batch, keys in out.items() if keys & pending.keys()}
        new = {k: p for k, p in pending.items() if not any(k in keys for keys in out.values())}
        if new:
            # The system prompt is marked for caching only here, so request keys (and the answers kept by them)
            # stay what they were before caching.
            batch = self.client.messages.batches.create(
                requests=[{"custom_id": k, "params": {**p, "system": cached_system(p["system"])}}
                          for k, p in new.items()])
            self._batches.mkdir(parents=True, exist_ok=True)
            (self._batches / f"{batch.id}.json").write_text(json.dumps(sorted(new)))
            self.notify(f"batch {batch.id}: sent {len(new)} request{'s' * (len(new) != 1)}")
            waiting.add(batch.id)
        for batch in sorted(waiting):
            self._collect(batch)
        for key in pending.keys() - self.failed.keys():  # never queue a call again that a batch left unanswered
            if not (self._answers / f"{key}.json").exists():
                self.failed[key] = "the batch returned no result for this request"

    def _collect(self, batch_id: str):
        """Wait for the batch to end, then keep its answers on disk and note what it didn't answer."""
        said = None
        while (batch := self.client.messages.batches.retrieve(batch_id)).processing_status != "ended":
            c = batch.request_counts
            if (line := f"batch {batch_id}: {c.succeeded + c.errored} of "
                        f"{c.processing + c.succeeded + c.errored + c.canceled + c.expired} done") != said:
                self.notify(line)
                said = line
            time.sleep(self.poll)
        self._answers.mkdir(parents=True, exist_ok=True)
        for item in self.client.messages.batches.results(batch_id):
            key, result = item.custom_id, item.result
            if result.type != "succeeded":
                error = getattr(getattr(getattr(result, "error", None), "error", None), "message", "")
                self.failed[key] = f"batch request {result.type}" + (f": {error}" if error else "")
                continue
            message = result.message
            if message.stop_reason in ("refusal", "max_tokens"):
                why = "Claude declined the request" if message.stop_reason == "refusal" else "Output truncated"
                self.failed[key] = f"{why} (batch {batch_id})"
                continue
            self.usage.add_reply(message.usage)
            text = "".join(block.text for block in message.content if block.type == "text")
            (self._answers / f"{key}.json").write_text(json.dumps({"text": text}))
        (self._batches / f"{batch_id}.json").unlink(missing_ok=True)
        self.notify(f"batch {batch_id}: collected")
