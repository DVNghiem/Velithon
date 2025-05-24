import pytest

from tests.util import get, post

# router.add_route("/inject/query", InjectQueryEndpoint, methods=["GET"])
# router.add_route("/inject/query/item", InjectQueryItemEndpoint, methods=["GET"])
# router.add_route("/inject/path/{name}", InjectPathEndpoint, methods=["GET"])
# router.add_route("/inject/body", InjectBodyEndpoint, methods=["POST"])
# router.add_route("/inject/headers", InjectHeadersEndpoint, methods=["GET"])
# router.add_route("/inject/request", InjectRequestEndpoint, methods=["GET"])

# InjectQueryEndpoint
@pytest.mark.benchmark
def test_get_validate_success(session):
    res = get("/inject/query?name=test&age=10")
    assert 200 == res.status_code

@pytest.mark.benchmark
def test_get_validate_fail(session):
    res = get("/inject/query")
    assert 200 != res.status_code

# InjectQueryItemEndpoint
@pytest.mark.benchmark
def test_inject_query_item_success(session):
    res = get("/inject/query/item?name=test&description=test")
    assert 200 == res.status_code

@pytest.mark.benchmark
def test_inject_query_item_fail(session):
    res = get("/inject/query/item?description=test")
    assert 400 == res.status_code

# InjectPathEndpoint
@pytest.mark.benchmark
def test_inject_path_success(session):
    res = get("/inject/path/test")
    assert 200 == res.status_code

@pytest.mark.benchmark
def test_inject_path_fail(session):
    res = get("/inject/path")
    assert 404 == res.status_code

# InjectBodyEndpoint
@pytest.mark.benchmark
def test_inject_body_success(session):
    res = post("/inject/body", data={"name": "test", "age": 20})
    assert 200 == res.status_code

@pytest.mark.benchmark
def test_inject_body_fail(session):
    res = post("/inject/body")
    assert 200 != res.status_code

# InjectHeadersEndpoint
@pytest.mark.benchmark
def test_inject_headers_success(session):
    res = get("/inject/headers", headers={"name": "test", "description": "test"})
    assert 200 == res.status_code

# InjectRequestEndpoint
@pytest.mark.benchmark
def test_inject_request_success(session):
    res = get("/inject/request")
    assert 200 == res.status_code