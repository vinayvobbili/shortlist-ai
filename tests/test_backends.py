"""The local backend: a long posting that runs out of output tokens gets another try with more room;
a model stuck repeating itself gets one try with some randomness."""

import json
import sys
import types

import pytest
from pydantic import BaseModel

from shortlist_ai import backends


class Out(BaseModel):
    items: list[str]


FULL = '{"items": ["a", "b", "c"]}'


@pytest.fixture
def generator(monkeypatch):
    """A stand-in for the on-device model: output is cut off below `needs` tokens."""
    monkeypatch.setitem(sys.modules, "outlines.inputs", types.SimpleNamespace(Chat=lambda messages: messages))
    budgets = []

    def make(needs):
        def generate(prompt, output_type, max_tokens):
            budgets.append(max_tokens)
            return FULL if max_tokens >= needs else FULL[:12]
        monkeypatch.setattr(backends, "_load_local_generator", lambda model: generate)
        return budgets
    return make


def test_truncated_output_is_retried_with_more_room(generator):
    budgets = generator(needs=3000)
    out = backends.LocalBackend(max_tokens=1000).structured("sys", [{"type": "text", "text": "posting"}], Out)
    assert out.items == ["a", "b", "c"] and budgets == [1000, 2000, 4000]


def test_gives_up_after_four_times_the_budget(generator):
    budgets = generator(needs=10**6)
    with pytest.raises(backends.BackendError, match="at 4000 tokens"):
        backends.LocalBackend(max_tokens=1000).structured("sys", [{"type": "text", "text": "posting"}], Out)
    assert budgets == [1000, 2000, 4000]


STUCK = '{"items": ["a", "' + "Customer Value Reinforcement, " * 400


@pytest.fixture
def stuck_model(monkeypatch):
    """A stand-in model that repeats itself until it samples with some randomness."""
    monkeypatch.setitem(sys.modules, "outlines.inputs", types.SimpleNamespace(Chat=lambda messages: messages))
    monkeypatch.setattr(backends, "_loop_breaker", lambda: "sampler")
    calls = []

    def install(unstuck: bool):
        def generate(prompt, output_type, max_tokens, **options):
            calls.append((max_tokens, options.get("sampler")))
            return FULL if unstuck and options.get("sampler") else STUCK
        monkeypatch.setattr(backends, "_load_local_generator", lambda model: generate)
        return calls
    return install


def test_a_stuck_model_gets_one_try_with_randomness_not_more_room(stuck_model):
    calls = stuck_model(unstuck=True)
    out = backends.LocalBackend(max_tokens=1000).structured("sys", [{"type": "text", "text": "resume"}], Out)
    assert out.items == ["a", "b", "c"] and calls == [(1000, None), (1000, "sampler")]


def test_a_model_still_stuck_fails_at_once_and_says_why(stuck_model):
    calls = stuck_model(unstuck=False)
    with pytest.raises(backends.BackendError, match="stuck repeating itself"):
        backends.LocalBackend(max_tokens=1000).structured("sys", [{"type": "text", "text": "resume"}], Out)
    assert calls == [(1000, None), (1000, "sampler")]


def test_looping_tells_repetition_from_ordinary_long_output():
    varied = json.dumps({"items": [f"skill {i}: built {i * 7} things for team {i % 13}" for i in range(400)]})
    assert backends._looping(STUCK)
    assert not backends._looping(varied)
    assert not backends._looping(STUCK[:3000])  # too short to tell
