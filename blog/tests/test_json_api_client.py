import pytest
from pytest_httpx import HTTPXMock

from blog.remote_api import JSONAPIClient


@pytest.mark.parametrize("base_url", ["http://test/blog", "http://test/blog/"])
def test_get_detail_url(json_api_client, base_url) -> None:
    json_api_client.base_url = base_url
    url = json_api_client.get_detail_url(33)
    expected_url = "http://test/blog/33"
    assert url == expected_url


def test_retrieve(json_api_client: JSONAPIClient, httpx_mock: HTTPXMock) -> None:
    pk = 33
    url = json_api_client.get_detail_url(pk)
    expected_data = {"test": "ok"}
    httpx_mock.add_response(method="GET", url=url, json=expected_data, status_code=200)
    result = json_api_client.retrieve(pk)
    assert result == expected_data


def test_retrieve_list(json_api_client: JSONAPIClient, httpx_mock: HTTPXMock) -> None:
    expected_data = {"test": "ok"}
    httpx_mock.add_response(
        method="GET", url=json_api_client.base_url, json=expected_data, status_code=200
    )
    result = json_api_client.retrieve_list()
    assert result == expected_data


def test_update(json_api_client: JSONAPIClient, httpx_mock: HTTPXMock) -> None:
    pk = 33
    url = json_api_client.get_detail_url(pk)
    expected_data = {"test": "ok"}
    httpx_mock.add_response(method="PUT", url=url, json=expected_data, status_code=200)
    result = json_api_client.update(pk, data=expected_data)
    assert result == expected_data


def test_create(json_api_client: JSONAPIClient, httpx_mock: HTTPXMock) -> None:
    expected_data = {"test": "ok"}
    httpx_mock.add_response(
        method="POST", url=json_api_client.base_url, json=expected_data, status_code=201
    )
    result = json_api_client.create(data=expected_data)
    assert result == expected_data


def test_delete(json_api_client: JSONAPIClient, httpx_mock: HTTPXMock) -> None:
    pk = 33
    url = json_api_client.get_detail_url(pk)
    httpx_mock.add_response(method="DELETE", url=url, status_code=204)
    json_api_client.delete(pk)
