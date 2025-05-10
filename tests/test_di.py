import pytest

from tests.util import get


@pytest.mark.benchmark
def test_di_single_provider(session):
    res = get("/di/singleton")
    assert 200 == res.status_code

@pytest.mark.benchmark
def test_di_factory_provider(session):
    res = get("/di/factory")
    assert 200 == res.status_code

@pytest.mark.benchmark
def test_di_async_factory_provider(session):
    res = get("/di/async-factory")
    print("res =>>>", res.text)
    assert 200 == res.status_code