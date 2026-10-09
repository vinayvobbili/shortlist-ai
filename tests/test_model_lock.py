"""Programs using the local model take turns on the GPU (ModelLock), across processes and threads."""

import os
import subprocess
import sys
import textwrap
import threading
import time
import types

import pytest
from pydantic import BaseModel

from shortlist_ai import backends
from shortlist_ai.backends import BackendError, LocalBackend, ModelLock


class Out(BaseModel):
    items: list[str]


FULL = '{"items": ["a"]}'
TEXT = [{"type": "text", "text": "posting"}]


@pytest.fixture
def fake_model(monkeypatch):
    """A stand-in for the on-device model that records when each generation ran."""
    monkeypatch.setitem(sys.modules, "outlines.inputs", types.SimpleNamespace(Chat=lambda messages: messages))
    calls = []

    def install(behaviour=None):
        def generate(prompt, output_type, max_tokens):
            calls.append(time.monotonic())
            return behaviour(len(calls)) if behaviour else FULL
        monkeypatch.setattr(backends, "_load_local_generator", lambda model: generate)
        return calls
    return install


def lock(tmp_path, **kw):
    return ModelLock(tmp_path / "local-model.lock", **kw)


def can_take(path) -> bool:
    return subprocess.run([sys.executable, "-c", textwrap.dedent(f"""
        import fcntl, sys
        f = open({str(path)!r}, "a+")
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            sys.exit(1)
        """)]).returncode == 0


def test_a_call_waits_for_another_process_and_names_it(tmp_path, fake_model):
    calls = fake_model()
    path = tmp_path / "local-model.lock"
    holder = subprocess.Popen([sys.executable, "-c", textwrap.dedent(f"""
        import fcntl, os, sys, time
        f = open({str(path)!r}, "a+")
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0); f.truncate(); f.write(str(os.getpid())); f.flush()
        print("held", flush=True)
        time.sleep(1.0)
        """)], stdout=subprocess.PIPE, text=True)
    try:
        assert holder.stdout.readline().strip() == "held"
        said = []
        start = time.monotonic()
        out = LocalBackend(lock=lock(tmp_path, notify=said.append)).structured("sys", TEXT, Out)
        assert out.items == ["a"]
        assert calls[0] - start >= 0.5                       # it ran only after the other process let go
        assert said == [f"waiting for another process using the local model (pid {holder.pid})"]
    finally:
        holder.wait(5)


def test_threads_of_one_process_take_turns(tmp_path, fake_model):
    running, overlap = [], []

    def behaviour(_):
        running.append(1)
        overlap.append(len(running))
        time.sleep(0.2)
        running.pop()
        return FULL
    fake_model(behaviour)
    backend = LocalBackend(lock=lock(tmp_path, notify=lambda m: None))
    threads = [threading.Thread(target=backend.structured, args=("sys", TEXT, Out)) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(10)
    assert overlap == [1, 1, 1]


def test_the_lock_is_not_held_between_calls(tmp_path, fake_model):
    fake_model()
    LocalBackend(lock=lock(tmp_path)).structured("sys", TEXT, Out)
    assert can_take(tmp_path / "local-model.lock")
    assert (tmp_path / "local-model.lock").read_text() == ""   # no stale pid left behind


def test_the_lock_is_released_when_generation_fails(tmp_path, fake_model):
    def boom(_):
        raise ValueError("model exploded")
    fake_model(boom)
    with pytest.raises(ValueError, match="exploded"):
        LocalBackend(lock=lock(tmp_path)).structured("sys", TEXT, Out)
    assert can_take(tmp_path / "local-model.lock")


def test_waiting_can_time_out_with_a_clear_error(tmp_path):
    first = lock(tmp_path)
    with first.held():
        with pytest.raises(BackendError, match=rf"Gave up after 0.3s .*pid {os.getpid()}"):
            with lock(tmp_path, timeout=0.3, notify=lambda m: None).held():
                pass


def test_timeout_from_the_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("SHORTLIST_MODEL_LOCK_TIMEOUT", "2.5")
    assert lock(tmp_path).timeout == 2.5 and lock(tmp_path, timeout=1).timeout == 1


def test_out_of_gpu_memory_is_retried_once(tmp_path, fake_model, monkeypatch):
    monkeypatch.setattr(LocalBackend, "OOM_PAUSE", 0)

    def behaviour(n):
        if n == 1:
            raise RuntimeError("[METAL] Command buffer execution failed: Insufficient Memory "
                               "(00000008:kIOGPUCommandBufferCallbackErrorOutOfMemory)")
        return FULL
    calls = fake_model(behaviour)
    assert LocalBackend(lock=lock(tmp_path)).structured("sys", TEXT, Out).items == ["a"]
    assert len(calls) == 2


def test_out_of_gpu_memory_twice_fails(tmp_path, fake_model, monkeypatch):
    monkeypatch.setattr(LocalBackend, "OOM_PAUSE", 0)

    def behaviour(_):
        raise RuntimeError("[METAL] Command buffer execution failed: Insufficient Memory")
    calls = fake_model(behaviour)
    with pytest.raises(RuntimeError, match="Insufficient Memory"):
        LocalBackend(lock=lock(tmp_path)).structured("sys", TEXT, Out)
    assert len(calls) == 2


def test_other_runtime_errors_are_not_retried(tmp_path, fake_model):
    def behaviour(_):
        raise RuntimeError("shape mismatch")
    calls = fake_model(behaviour)
    with pytest.raises(RuntimeError, match="shape mismatch"):
        LocalBackend(lock=lock(tmp_path)).structured("sys", TEXT, Out)
    assert len(calls) == 1
