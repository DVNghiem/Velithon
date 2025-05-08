import pytest

from tests.util import delete, get, post, put


@pytest.mark.benchmark
def test_get(session):
    res = get("/endpoint")
    assert 200 == res.status_code

@pytest.mark.benchmark
def test_post(session):
    res = post("/endpoint")
    assert 200 == res.status_code

@pytest.mark.benchmark
def test_put(session):
    res = put("/endpoint")
    assert 200 == res.status_code

@pytest.mark.benchmark
def test_delete(session):
    res = delete("/endpoint")
    assert 200 == res.status_code