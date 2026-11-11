"""The OpenAI-compatible backend is the local backend's client pointed at a hosted API: it sends the bearer key and
the model, and tells a refused key, a rate limit and a 5xx apart from a job it can't score."""

import pytest
from test_backends import FULL, POSTING, FakeServer, Out, completion

from shortlist_ai import backends

KEY = "test-key-0000"


@pytest.fixture
def server():
    fake = FakeServer()
    yield fake
    fake.httpd.shutdown()
    fake.httpd.server_close()


def make(server, **kw):
    return backends.OpenAIBackend("acme/test-model", server.url, KEY, provider="acme", **kw)


def test_it_sends_the_bearer_key_and_the_model(server):
    out = make(server).structured("sys", POSTING, Out)
    assert out.items == ["a", "b", "c"]
    assert server.headers[0]["Authorization"] == f"Bearer {KEY}"
    (path, body), = server.requests
    assert path == "/v1/chat/completions"
    assert body["model"] == "acme/test-model"
    assert body["response_format"]["type"] == "json_schema"


def test_the_key_never_appears_in_an_error(server):
    server.reply = lambda body: (500, {"error": {"message": "boom"}})
    with pytest.raises(backends.BackendError) as caught:
        make(server).structured("sys", POSTING, Out)
    assert KEY not in str(caught.value)


def test_a_429_names_the_provider_and_the_status(server):
    server.reply = lambda body: (429, {"error": {"message": "Too many requests"}})
    with pytest.raises(backends.BackendError, match=r"The acme API at http://.* answered 429: Too many requests"):
        make(server).structured("sys", POSTING, Out)


def test_a_5xx_reads_as_the_api_answering_5xx(server):
    server.reply = lambda body: (503, {"error": "overloaded"})
    with pytest.raises(backends.BackendError, match=r"API at http://\S+ answered 503: overloaded"):
        make(server).structured("sys", POSTING, Out)


@pytest.mark.parametrize("code", [401, 403])
def test_a_refused_key_says_so(server, code):
    server.reply = lambda body: (code, {"error": {"message": "invalid api key"}})
    with pytest.raises(backends.BackendError, match=rf"refused the key \({code}\): invalid api key"):
        make(server).structured("sys", POSTING, Out)


def test_an_empty_answer_is_a_failure(server):
    server.reply = lambda body: (200, completion("  "))
    with pytest.raises(backends.BackendError, match="answered with nothing"):
        make(server).structured("sys", POSTING, Out)


def test_unparseable_output_is_a_failure(server):
    server.reply = lambda body: (200, completion("sorry, I can't do that"))
    with pytest.raises(backends.BackendError, match="didn't validate"):
        make(server).structured("sys", POSTING, Out)


def test_fenced_json_is_read(server):
    server.reply = lambda body: (200, completion(f"```json\n{FULL}\n```"))
    assert make(server).structured("sys", POSTING, Out).items == ["a", "b", "c"]


def test_response_format_can_be_loosened(server):
    make(server, response_format="json_object").structured("sys", POSTING, Out)
    make(server, response_format="none").structured("sys", POSTING, Out)
    assert server.requests[0][1]["response_format"] == {"type": "json_object"}
    assert "response_format" not in server.requests[1][1]


def test_an_unknown_response_format_is_refused(server):
    with pytest.raises(ValueError, match="response_format"):
        make(server, response_format="xml")


def test_the_local_backend_still_sends_no_key(server, monkeypatch):
    monkeypatch.setenv("LOCAL_LLM_URL", server.url)
    backends.LocalBackend(max_tokens=1000).structured("sys", POSTING, Out)
    assert "Authorization" not in server.headers[0]
    assert server.requests[0][1]["model"] == "local"
