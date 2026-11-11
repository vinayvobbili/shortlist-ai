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


def reasoning_reply(content, thinking, finish="stop", field="reasoning_content"):
    reply = completion(content, finish)
    reply["choices"][0]["message"][field] = thinking
    return reply


@pytest.mark.parametrize("field", ["reasoning_content", "reasoning"])
def test_an_empty_content_takes_the_json_from_the_thinking(server, field):
    thinking = f'The schema is {{"items": []}}. So the answer is {FULL}'
    server.reply = lambda body: (200, reasoning_reply("", thinking, "length", field))
    assert make(server).structured("sys", POSTING, Out).items == ["a", "b", "c"]


def test_content_wins_over_the_thinking(server):
    server.reply = lambda body: (200, reasoning_reply(FULL, '{"items": ["x"]}'))
    assert make(server).structured("sys", POSTING, Out).items == ["a", "b", "c"]


def test_thinking_that_ran_out_of_room_is_retried_with_more(server):
    replies = iter([reasoning_reply("", "Let me think about this...", "length"), completion(FULL)])
    server.reply = lambda body: (200, next(replies))
    assert make(server, max_tokens=1000).structured("sys", POSTING, Out).items == ["a", "b", "c"]
    assert [body["max_tokens"] for _, body in server.requests] == [1000, 2000]


def test_a_length_finish_with_no_answer_is_a_clear_failure(server):
    server.reply = lambda body: (200, reasoning_reply("", "Hmm, still thinking...", "length"))
    with pytest.raises(backends.BackendError, match=r"ran out of output tokens \(finish_reason length\)") as caught:
        make(server, max_tokens=1000).structured("sys", POSTING, Out)
    assert "nothing" not in str(caught.value)
    assert [body["max_tokens"] for _, body in server.requests] == [1000, 2000, 4000]


def test_a_stop_with_no_answer_says_nothing_and_the_finish_reason(server):
    server.reply = lambda body: (200, completion("", "stop"))
    with pytest.raises(backends.BackendError, match=r"answered with nothing \(finish_reason stop\)"):
        make(server).structured("sys", POSTING, Out)


def test_openrouter_gets_the_reasoning_effort_and_others_do_not(server):
    make(server).structured("sys", POSTING, Out)
    assert "reasoning" not in server.requests[0][1]
    router = backends.OpenAIBackend("acme/m", "https://openrouter.ai/api/v1", KEY, provider="openrouter")
    assert router._reasoning_options() == {"reasoning": {"effort": "low"}}
    off = backends.OpenAIBackend("acme/m", "https://openrouter.ai/api/v1", KEY, reasoning_effort=None)
    assert off._reasoning_options() == {}


def waiting(server, **kw):
    backend = make(server, **kw)
    backend.slept = []
    backend.sleep = backend.slept.append
    return backend


def test_a_429_waits_what_retry_after_says_then_succeeds(server):
    replies = iter([(429, {"error": "slow down"}, {"Retry-After": "7"}), (200, completion(FULL))])
    server.reply = lambda body: next(replies)
    backend = waiting(server)
    assert backend.structured("sys", POSTING, Out).items == ["a", "b", "c"]
    assert backend.slept == [7.0]


def test_a_429_without_retry_after_backs_off_and_gives_up_after_the_retries(server):
    server.reply = lambda body: (429, {"error": {"message": "Too many requests"}})
    backend = waiting(server)
    with pytest.raises(backends.BackendError, match="answered 429: Too many requests") as caught:
        backend.structured("sys", POSTING, Out)
    assert backend.slept == [2.0, 4.0, 8.0, 16.0]
    assert len(server.requests) == 5
    assert caught.value.status == 429


def test_a_429_that_asks_for_a_long_wait_is_not_retried(server):
    server.reply = lambda body: (429, {"error": "daily limit"}, {"Retry-After": "3600"})
    backend = waiting(server)
    with pytest.raises(backends.BackendError, match="answered 429"):
        backend.structured("sys", POSTING, Out)
    assert backend.slept == [] and len(server.requests) == 1


def test_a_404_is_a_refused_model_and_not_retried(server):
    server.reply = lambda body: (404, {"detail": "Function 'abc': Not found for account"})
    backend = waiting(server)
    with pytest.raises(backends.BackendError, match=r"refused the model acme/test-model \(404\): Function 'abc'"):
        backend.structured("sys", POSTING, Out)
    assert len(server.requests) == 1


def test_retry_after_can_be_an_http_date():
    from datetime import datetime, timedelta, timezone
    from email.utils import format_datetime

    soon = format_datetime(datetime.now(timezone.utc) + timedelta(seconds=30), usegmt=True)
    assert 25 < backends._retry_after({"Retry-After": soon}) <= 30
    assert backends._retry_after({"Retry-After": "garbage"}) is None
    assert backends._retry_after({}) is None


def test_the_local_backend_still_sends_no_key(server, monkeypatch):
    monkeypatch.setenv("LOCAL_LLM_URL", server.url)
    backends.LocalBackend(max_tokens=1000).structured("sys", POSTING, Out)
    assert "Authorization" not in server.headers[0]
    assert server.requests[0][1]["model"] == "local"
