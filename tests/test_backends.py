"""The local backend talks to one shared OpenAI-compatible model server: a long posting that runs out of output
tokens gets another try with more room; a model stuck repeating itself gets one try with some randomness;
a server that is missing or can't serve raises BackendError."""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from pydantic import BaseModel

from shortlist_ai import backends


class Out(BaseModel):
    items: list[str]


FULL = '{"items": ["a", "b", "c"]}'
STUCK = '{"items": ["a", "' + "Customer Value Reinforcement, " * 400
POSTING = [{"type": "text", "text": "Initech is hiring a data engineer"}]


class FakeServer:
    """A stand-in model server. `reply(request_body)` returns (status, json) for each POST; requests are kept."""

    def __init__(self):
        self.requests = []
        self.headers = []
        self.reply = lambda body: (200, completion(FULL))
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                outer.requests.append((self.path, body))
                outer.headers.append(dict(self.headers))
                status, payload = outer.reply(body)
                data = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}/v1"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()


def completion(text, finish="stop", prompt_tokens=120, completion_tokens=30):
    return {"choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": finish}],
            "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens}}


@pytest.fixture
def server(monkeypatch):
    fake = FakeServer()
    monkeypatch.setenv("LOCAL_LLM_URL", fake.url)
    yield fake
    fake.httpd.shutdown()
    fake.httpd.server_close()


def test_structured_request_carries_the_schema_and_the_reply_is_parsed(server):
    out = backends.LocalBackend(max_tokens=1000).structured("sys", POSTING, Out)
    assert out.items == ["a", "b", "c"]
    (path, body), = server.requests
    assert path == "/v1/chat/completions"
    assert body["model"] == "local" and body["max_tokens"] == 1000
    assert body["response_format"] == {"type": "json_schema", "json_schema": {
        "name": "Out", "schema": Out.model_json_schema(), "strict": True}}
    assert [m["role"] for m in body["messages"]] == ["system", "user"]
    assert "Output JSON matching this schema" in body["messages"][0]["content"]
    assert "temperature" not in body


def test_the_model_argument_is_not_sent_to_the_server(server):
    backend = backends.LocalBackend(model="some-other-model", max_tokens=1000)
    backend.structured("sys", POSTING, Out)
    assert server.requests[0][1]["model"] == "local" and backend.model == backends.LOCAL_MODEL


def test_usage_is_recorded(server):
    backend = backends.LocalBackend(max_tokens=1000)
    backend.structured("sys", POSTING, Out)
    backend.structured("sys", POSTING, Out)
    assert (backend.usage.input_tokens, backend.usage.output_tokens, backend.usage.calls) == (240, 60, 2)


def test_truncated_output_is_retried_with_more_room(server):
    server.reply = lambda body: (200, completion(FULL if body["max_tokens"] >= 3000 else FULL[:12], "length"))
    out = backends.LocalBackend(max_tokens=1000).structured("sys", POSTING, Out)
    assert out.items == ["a", "b", "c"]
    assert [b["max_tokens"] for _, b in server.requests] == [1000, 2000, 4000]


def test_gives_up_after_four_times_the_budget(server):
    server.reply = lambda body: (200, completion(FULL[:12], "length"))
    with pytest.raises(backends.BackendError, match="at 4000 tokens"):
        backends.LocalBackend(max_tokens=1000).structured("sys", POSTING, Out)
    assert [b["max_tokens"] for _, b in server.requests] == [1000, 2000, 4000]


def test_a_stuck_model_gets_one_try_with_randomness_not_more_room(server):
    server.reply = lambda body: (200, completion(FULL if "temperature" in body else STUCK, "length"))
    out = backends.LocalBackend(max_tokens=1000).structured("sys", POSTING, Out)
    first, second = (b for _, b in server.requests)
    assert out.items == ["a", "b", "c"]
    assert "temperature" not in first and second["temperature"] == 0.5 and second["top_p"] == 0.95
    assert first["max_tokens"] == second["max_tokens"] == 1000


def test_a_model_still_stuck_fails_at_once_and_says_why(server):
    server.reply = lambda body: (200, completion(STUCK, "length"))
    with pytest.raises(backends.BackendError, match="stuck repeating itself"):
        backends.LocalBackend(max_tokens=1000).structured("sys", POSTING, Out)
    assert len(server.requests) == 2


def test_a_503_raises_with_the_servers_message(server):
    server.reply = lambda body: (503, {"error": {"message": "memory is critical, try again later"}})
    with pytest.raises(backends.BackendError, match=r"503.*memory is critical, try again later"):
        backends.LocalBackend().structured("sys", POSTING, Out)


def test_a_plain_error_string_is_passed_on(server):
    server.reply = lambda body: (500, {"error": "model failed to load"})
    with pytest.raises(backends.BackendError, match=r"500.*model failed to load"):
        backends.LocalBackend().structured("sys", POSTING, Out)


def test_no_server_raises_naming_the_url(monkeypatch):
    monkeypatch.setenv("LOCAL_LLM_URL", "http://127.0.0.1:9/v1")
    with pytest.raises(backends.BackendError, match=r"no local model server at http://127\.0\.0\.1:9/v1.*LOCAL_LLM_URL"):
        backends.LocalBackend().structured("sys", POSTING, Out)


def test_a_slow_server_times_out_with_a_clear_message(server):
    def slow(body):
        time.sleep(1)
        return 200, completion(FULL)
    server.reply = slow
    with pytest.raises(backends.BackendError, match="timed out"):
        backends.LocalBackend(timeout=0.2).structured("sys", POSTING, Out)


def test_the_default_url_is_the_shared_server(monkeypatch):
    monkeypatch.delenv("LOCAL_LLM_URL")
    assert backends.LocalBackend().url == "http://127.0.0.1:8010/v1"


def test_a_document_without_text_is_refused_before_any_request(server):
    with pytest.raises(backends.BackendError, match="needs text"):
        backends.LocalBackend().structured("sys", [{"type": "text", "text": "  "}], Out)
    assert server.requests == []


def test_looping_tells_repetition_from_ordinary_long_output():
    varied = json.dumps({"items": [f"skill {i}: built {i * 7} things for team {i % 13}" for i in range(400)]})
    assert backends._looping(STUCK)
    assert not backends._looping(varied)
    assert not backends._looping(STUCK[:3000])  # too short to tell
