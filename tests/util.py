from typing import Optional

import requests

BASE_URL = "http://127.0.0.1:5005"


def check_response(response: requests.Response, expected_status_code: int):
    assert response.status_code == expected_status_code
    assert response.headers.get("global_after") == "global_after_request"
    assert "server" in response.headers


def get(
    endpoint: str,
    expected_status_code: int = 200,
    headers: dict = {},
    should_check_response: bool = False,
) -> requests.Response:
    """
    Makes a GET request to the given endpoint and checks the response.

    endpoint str: The endpoint to make the request to.
    expected_status_code int: The expected status code of the response.
    headers dict: The headers to send with the request.
    should_check_response bool: A boolean to indicate if the status code and headers should be checked.
    """
    endpoint = endpoint.strip("/")
    response = requests.get(f"{BASE_URL}/{endpoint}", headers=headers)
    if should_check_response:
        check_response(response, expected_status_code)
    return response


def post(
    endpoint: str,
    data: Optional[dict] = None,
    expected_status_code: int = 200,
    headers: dict = {},
    should_check_response: bool = False,
) -> requests.Response:
    """
    Makes a POST request to the given endpoint and checks the response.

    endpoint str: The endpoint to make the request to.
    data Optional[dict]: The data to send with the request.
    expected_status_code int: The expected status code of the response.
    headers dict: The headers to send with the request.
    should_check_response bool: A boolean to indicate if the status code and headers should be checked.
    """
    endpoint = endpoint.strip("/")
    response = requests.post(f"{BASE_URL}/{endpoint}", json=data, headers=headers)
    if should_check_response:
        check_response(response, expected_status_code)
    return response


def multipart_post(
    endpoint: str,
    files: Optional[dict] = None,
    expected_status_code: int = 200,
    should_check_response: bool = False,
) -> requests.Response:
    """
    Makes a POST request to the given endpoint and checks the response.

    endpoint str: The endpoint to make the request to.
    files Optional[dict]: The files to send with the request.
    expected_status_code int: The expected status code of the response.
    should_check_response bool: A boolean to indicate if the status code and headers should be checked.
    """
    endpoint = endpoint.strip("/")
    response = requests.post(f"{BASE_URL}/{endpoint}", files=files)
    if should_check_response:
        check_response(response, expected_status_code)
    return response


def put(
    endpoint: str,
    data: Optional[dict] = None,
    expected_status_code: int = 200,
    headers: dict = {},
    should_check_response: bool = False,
) -> requests.Response:
    """
    Makes a PUT request to the given endpoint and checks the response.

    endpoint str: The endpoint to make the request to.
    expected_status_code int: The expected status code of the response.
    headers dict: The headers to send with the request.
    should_check_response bool: A boolean to indicate if the status code and headers should be checked.
    """
    endpoint = endpoint.strip("/")
    response = requests.put(f"{BASE_URL}/{endpoint}", json=data, headers=headers)
    if should_check_response:
        check_response(response, expected_status_code)
    return response


def delete(
    endpoint: str,
    data: Optional[dict] = None,
    expected_status_code: int = 200,
    headers: dict = {},
    should_check_response: bool = False,
) -> requests.Response:
    """
    Makes a DELETE request to the given endpoint and checks the response.

    endpoint str: The endpoint to make the request to.
    expected_status_code int: The expected status code of the response.
    headers dict: The headers to send with the request.
    should_check_response bool: A boolean to indicate if the status code and headers should be checked.
    """
    endpoint = endpoint.strip("/")
    response = requests.delete(f"{BASE_URL}/{endpoint}", json=data, headers=headers)
    if should_check_response:
        check_response(response, expected_status_code)
    return response