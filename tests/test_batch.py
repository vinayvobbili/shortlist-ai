"""The batch backend: calls with no answer are queued and sent as one batch per round, answers are kept on disk,
a batch still out when a run stopped is collected rather than sent again, and calls a batch didn't answer fail
instead of being queued for ever."""

import json
from types import SimpleNamespace as NS

import pytest
from pydantic import BaseModel

from shortlist_ai.backends import BackendError
from shortlist_ai.batch import BatchBackend, Deferred


class Out(BaseModel):
    value: str


class FakeBatches:
    """The Message Batches API: answer(params) gives the reply text, or a result type ("errored", "refusal")."""

    def __init__(self, answer, polls: int = 1):
        self.answer, self.polls = answer, polls
        self.sent: dict[str, list] = {}
        self._seen: dict[str, int] = {}

    def create(self, requests):
        batch_id = f"msgbatch_{len(self.sent) + 1}"
        self.sent[batch_id] = list(requests)
        return NS(id=batch_id)

    def retrieve(self, batch_id):
        self._seen[batch_id] = self._seen.get(batch_id, 0) + 1
        ended = self._seen[batch_id] > self.polls
        n = len(self.sent[batch_id])
        return NS(processing_status="ended" if ended else "in_progress",
                  request_counts=NS(processing=0 if ended else n, succeeded=n if ended else 0, errored=0,
                                    canceled=0, expired=0))

    def results(self, batch_id):
        for r in self.sent[batch_id]:
            reply = self.answer(r["params"])
            if reply == "errored":
                yield NS(custom_id=r["custom_id"], result=NS(type="errored", error=NS(error=NS(message="overloaded"))))
                continue
            stop = "refusal" if reply == "refusal" else "end_turn"
            text = json.dumps({"value": reply})
            yield NS(custom_id=r["custom_id"], result=NS(type="succeeded", message=NS(
                stop_reason=stop, usage=NS(input_tokens=10, output_tokens=5),
                content=[NS(type="thinking", thinking="..."), NS(type="text", text=text)])))


def backend(tmp_path, answer, polls=1):
    batches = FakeBatches(answer, polls)
    return BatchBackend(tmp_path, model="claude-test", client=NS(messages=NS(batches=batches)), poll=0,
                        notify=lambda msg: None), batches


def echo(params):
    return "re: " + params["messages"][0]["content"][0]["text"]


def ask(b, text):
    return b.structured("sys", [{"type": "text", "text": text}], Out).value


def test_dependent_calls_go_out_in_rounds_and_answers_are_kept(tmp_path):
    b, batches = backend(tmp_path, echo)

    def work():  # like the pipeline: each job's second call needs its first's answer, and a job that waits fails
        out = []
        for t in ("a", "b"):
            try:
                out.append(ask(b, ask(b, t)))
            except Deferred:
                pass
        return out

    assert b.run(work) == ["re: re: a", "re: re: b"]
    assert [len(reqs) for reqs in batches.sent.values()] == [2, 2]  # both firsts, then both seconds
    first = batches.sent["msgbatch_1"][0]["params"]
    assert first["model"] == "claude-test" and first["output_config"]["format"]["type"] == "json_schema"
    assert b.usage.calls == 4

    again, more = backend(tmp_path, echo)  # a second run answers everything from disk
    assert again.run(work) == ["re: re: a", "re: re: b"] and more.sent == {}


def test_a_call_without_an_answer_is_deferred(tmp_path):
    b, _ = backend(tmp_path, echo)
    with pytest.raises(Deferred):
        ask(b, "a")
    assert len(b.pending) == 1


def test_a_batch_still_out_is_collected_not_sent_again(tmp_path):
    b, batches = backend(tmp_path, echo)
    with pytest.raises(Deferred):
        ask(b, "a")
    batch = batches.create([{"custom_id": k, "params": p} for k, p in b.pending.items()])
    (tmp_path / "batches").mkdir()
    (tmp_path / "batches" / f"{batch.id}.json").write_text(json.dumps(list(b.pending)))  # the run stopped here

    later = BatchBackend(tmp_path, model="claude-test", client=NS(messages=NS(batches=batches)), poll=0,
                         notify=lambda msg: None)
    assert later.run(lambda: ask(later, "a")) == "re: a"
    assert list(batches.sent) == ["msgbatch_1"] and not list((tmp_path / "batches").iterdir())


@pytest.mark.parametrize(("reply", "says"), [("errored", "batch request errored: overloaded"),
                                             ("refusal", "Claude declined the request")])
def test_a_call_the_batch_did_not_answer_fails_and_is_retried_next_run(tmp_path, reply, says):
    replies = {"bad": reply}
    b, batches = backend(tmp_path, lambda p: replies.get(p["messages"][0]["content"][0]["text"], "fine"))

    def work():
        out = {}
        for t in ("ok", "bad"):
            try:
                out[t] = ask(b, t)
            except BackendError as e:
                out[t] = str(e)
            except Deferred:
                pass
        return out

    result = b.run(work)
    assert result["ok"] == "fine" and says in result["bad"] and len(batches.sent) == 1
    replies.clear()
    retry, more = backend(tmp_path, lambda p: "fine now")
    assert retry.run(lambda: ask(retry, "bad")) == "fine now" and len(more.sent) == 1


def test_a_round_that_queues_nothing_returns_at_once(tmp_path):
    b, batches = backend(tmp_path, echo)
    assert b.run(lambda: 42) == 42 and batches.sent == {}
