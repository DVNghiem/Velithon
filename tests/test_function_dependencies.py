"""Test function dependency injection functionality."""

import pytest

from tests.util import get


@pytest.mark.benchmark
def test_function_dependency_with_admin_user(session):
    """Test function dependency with admin user."""
    response = get('/function-deps', headers={'X-User-ID': 'admin'})

    assert response.status_code == 200
    data = response.json()

    assert data['user_id'] == 'admin'
    assert data['permissions'] == ['read', 'write', 'delete']
    assert data['constant'] == 'constant_value'


@pytest.mark.benchmark
def test_function_dependency_with_regular_user(session):
    """Test function dependency with regular user."""
    response = get('/function-deps', headers={'X-User-ID': 'user'})

    assert response.status_code == 200
    data = response.json()

    assert data['user_id'] == 'user'
    assert data['permissions'] == ['read', 'write']
    assert data['constant'] == 'constant_value'


@pytest.mark.benchmark
def test_function_dependency_with_anonymous_user(session):
    """Test function dependency with anonymous user."""
    response = get('/function-deps')

    assert response.status_code == 200
    data = response.json()

    assert data['user_id'] == 'anonymous'
    assert data['permissions'] == ['read']
    assert data['constant'] == 'constant_value'


@pytest.mark.benchmark
def test_simple_function_dependency(session):
    """Test simple function dependency."""
    response = get('/function-deps/simple', headers={'X-User-ID': 'test_user'})

    assert response.status_code == 200
    data = response.json()

    assert data['user_id'] == 'test_user'
