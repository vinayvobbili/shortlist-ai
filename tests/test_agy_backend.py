"""The agy backend: parses a SUCCESS reply and turns every failure into BackendError (subprocess mocked)."""

import json
import subprocess
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from shortlist_ai import backends


class Out(BaseModel):
    items: list[str]


CONTENT = [{"type": "text", "text": "posting"}]


def reply(response='{"items": ["a"]}', status="SUCCESS"):
    return json.dumps({"status": status, "response": response, "usage": {"input_tokens": 7, "output_tokens": 3}})


@pytest.fixture
def run(monkeypatch):
    calls = []

    def make(stdout="", returncode=0, stderr="", raises=None):
        def fake(args, **kw):
            calls.append((args, kw))
            if raises:
                raise raises
            return SimpleNamespace(stdout=stdout, returncode=returncode, stderr=stderr)
        monkeypatch.setattr(backends.subprocess, "run", fake)
        monkeypatch.setattr(backends.shutil, "which", lambda name: "/bin/agy")
        return calls
    return make


def test_success_is_parsed_and_runs_sandboxed_in_an_empty_directory(run):
    calls = run(reply())
    b = backends.AgyBackend()
    assert b.structured("system", CONTENT, Out).items == ["a"]
    args, kw = calls[0]
    assert "--sandbox" in args and "--dangerously-skip-permissions" not in args
    assert args[args.index("--model") + 1] == backends.AGY_MODEL and "system" in args[2]
    assert kw["stdin"] == subprocess.DEVNULL and kw["timeout"] == b.timeout
    assert kw["cwd"] != "." and (b.usage.input_tokens, b.usage.output_tokens) == (7, 3)


def test_fenced_json_is_accepted(run):
    run(reply('```json\n{"items": ["x"]}\n```'))
    assert backends.AgyBackend().structured("s", CONTENT, Out).items == ["x"]


@pytest.mark.parametrize("kwargs, match", [
    (dict(stdout=reply("boom", status="ERROR")), "status ERROR"),
    (dict(stdout=reply("Quota exceeded", status="ERROR")), "quota"),
    (dict(stdout="", returncode=1, stderr="429 Too Many Requests"), "quota or rate limit"),
    (dict(stdout="not json"), "agy failed"),
    (dict(stdout=reply("not the schema")), "didn't validate"),
    (dict(raises=subprocess.TimeoutExpired("agy", 1)), "didn't answer"),
    (dict(raises=OSError("nope")), "couldn't start"),
])
def test_failures_raise_backend_error(run, kwargs, match):
    run(**kwargs)
    with pytest.raises(backends.BackendError, match=match):
        backends.AgyBackend().structured("s", CONTENT, Out)


def test_missing_binary(monkeypatch):
    monkeypatch.setattr(backends.shutil, "which", lambda name: None)
    with pytest.raises(backends.BackendError, match="isn't installed"):
        backends.AgyBackend().structured("s", CONTENT, Out)


def test_no_text_is_an_error_and_get_backend_knows_agy():
    with pytest.raises(backends.BackendError, match="needs text"):
        backends.AgyBackend().structured("s", [{"type": "document"}], Out)
    assert backends.get_backend("agy", "gemini-3.8-flash-medium").model == "gemini-3.8-flash-medium"
    assert backends.get_backend("agy").model == backends.AGY_MODEL


def test_an_answer_with_every_list_empty_gets_one_more_try(monkeypatch, run):
    replies = iter([reply('{"items": []}'), reply('{"items": ["a"]}')])
    calls = run(reply())
    monkeypatch.setattr(backends.subprocess, "run", lambda args, **kw: (
        calls.append(args), SimpleNamespace(stdout=next(replies), returncode=0, stderr=""))[1])
    assert backends.AgyBackend().structured("s", CONTENT, Out).items == ["a"]
    run(reply('{"items": []}'))  # still empty the second time: believed
    assert backends.AgyBackend().structured("s", CONTENT, Out).items == []
