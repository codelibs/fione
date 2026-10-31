"""The client against scripted responses: errors, redirects, odd bodies, encoding."""

import io
import pickle

import httpx
import pytest
from fione_sdk import Client, FioneError
from fione_sdk.client import _Body


def scripted(handler, **kwargs) -> tuple[Client, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    http = httpx.Client(
        transport=httpx.MockTransport(record), base_url="http://fione.test", **kwargs
    )
    return Client(token="secret", http=http), seen


def test_non_json_error_has_code_http():
    client, _ = scripted(lambda request: httpx.Response(502, text="Bad Gateway"))
    for call in (lambda: client.projects(), lambda: client.read("p", 1)):
        with pytest.raises(FioneError) as err:
            call()
        assert (err.value.status, err.value.code) == (502, "http")


def test_a_redirect_is_an_error_naming_the_location_and_is_not_followed():
    def handler(request):
        if request.url.host == "fione.test":
            return httpx.Response(302, headers={"Location": "https://elsewhere.test/api/v1/x"})
        return httpx.Response(200, json=[])

    # Even when the underlying client would follow redirects, the SDK does not.
    client, seen = scripted(handler, follow_redirects=True)
    for call in (lambda: client.projects(), lambda: client.read("p", 1)):
        with pytest.raises(FioneError) as err:
            call()
        assert (err.value.status, err.value.code) == (302, "http")
        assert "https://elsewhere.test/api/v1/x" in err.value.message
    assert {r.url.host for r in seen} == {"fione.test"}


def test_the_bearer_header_is_the_only_credential():
    client, seen = scripted(lambda request: httpx.Response(200, json=[]))
    client.projects()
    request = seen[0]
    assert request.headers["authorization"] == "Bearer secret"
    assert not {"cookie", "x-api-key"} & set(request.headers)


def test_a_non_json_success_is_an_error():
    client, _ = scripted(lambda request: httpx.Response(200, text="<html>portal</html>"))
    with pytest.raises(FioneError) as err:
        client.projects()
    assert (err.value.status, err.value.code) == (200, "http")
    assert err.value.message == "response is not JSON"


@pytest.mark.parametrize(("column", "segment"), [("..", "%2E%2E"), (".", "%2E"), ("a/b", "a%2Fb")])
def test_column_names_are_one_path_segment(column, segment):
    client, seen = scripted(lambda request: httpx.Response(200, json={}))
    client.column_profile("p", 1, column)
    assert seen[0].url.raw_path.decode() == f"/api/v1/projects/p/datasets/1/columns/{segment}"


def test_errors_survive_pickling():
    error = pickle.loads(pickle.dumps(FioneError(404, "not_found", "no such project")))
    assert (error.status, error.code, error.message) == (404, "not_found", "no such project")


def test_body_skips_empty_chunks():
    body = io.BufferedReader(_Body(iter([b"a,b\n1,", b"", b"2\n"])))
    assert body.read() == b"a,b\n1,2\n"
