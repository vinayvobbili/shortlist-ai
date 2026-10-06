"""The local backend: a long posting that runs out of output tokens gets another try with more room."""

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
