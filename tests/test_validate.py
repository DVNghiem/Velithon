import pytest

from tests.util import get, post


@pytest.mark.benchmark
def test_get_validate_success(session):
    res = get("/validate?id=1&name=test&description=test")
    assert 200 == res.status_code

@pytest.mark.benchmark
def test_get_validate_fail(session):
    res = get("/validate")
    assert 200 != res.status_code

@pytest.mark.benchmark
def test_post_validate_success(session):
    res = post("/validate", data={"id": 1, "name": "test", "description": "test"})
    assert 200 == res.status_code

@pytest.mark.benchmark
def test_post_validate_fail(session):
    res = post("/validate")
    assert 200 != res.status_code