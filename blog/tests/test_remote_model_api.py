import pytest
from httpx import HTTPStatusError
from pytest_httpx import HTTPXMock

from blog.models import Post
from blog.remote_api import RemoteAPIError
from blog.remote_api import RemoteModelAPI
from blog.serializers import RemotePostSerializer


@pytest.fixture()
def remote_posts_api(json_api_client) -> RemoteModelAPI:
    return RemoteModelAPI(json_api_client, "Posts", RemotePostSerializer)


@pytest.fixture()
def test_post() -> Post:
    return Post(
        id=1,
        user_id=1,
        title="test title",
        body="quia et suscipit",
    )


def test_serialize_object(remote_posts_api: RemoteModelAPI) -> None:
    post_data = {
        "id": 1,
        "user_id": 1,
        "title": "test title",
        "body": "quia et suscipit",
    }
    post = Post(**post_data)
    serializer = RemotePostSerializer(post)
    expected_data = serializer.data
    serialized_post = remote_posts_api.serialize_object(post)
    assert serialized_post == expected_data


@pytest.mark.django_db()
def test_get_initial_data(
    remote_posts_api: RemoteModelAPI, httpx_mock: HTTPXMock, posts_response: list[dict]
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=remote_posts_api.client.base_url,
        json=posts_response,
        status_code=200,
    )
    loaded_posts = remote_posts_api.get_initial_data()
    num_expected_posts = 2
    assert len(loaded_posts) == num_expected_posts
    for i, post in enumerate(loaded_posts):
        assert isinstance(post, Post)
        assert post.pk == posts_response[i]["id"]
        assert post.user_id == posts_response[i]["userId"]
        assert post.title == posts_response[i]["title"]
        assert post.body == posts_response[i]["body"]


def test_get_initial_data_empty_data(
    remote_posts_api: RemoteModelAPI, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=remote_posts_api.client.base_url,
        json=[],
        status_code=200,
    )
    loaded_posts = remote_posts_api.get_initial_data()
    num_expected_posts = 0
    assert len(loaded_posts) == num_expected_posts


def test_get_initial_data_invalid_data(
    remote_posts_api: RemoteModelAPI, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=remote_posts_api.client.base_url,
        json=[{"test": "invalid data"}],
        status_code=200,
    )
    with pytest.raises(RemoteAPIError) as exc_info:
        remote_posts_api.get_initial_data()
    expected_error_message = (
        "Error loading Posts: ["
        "{'id': [ErrorDetail(string='This field is required.', code='required')],"
        " 'userId': [ErrorDetail(string='This field is required.', code='required')],"
        " 'title': [ErrorDetail(string='This field is required.', code='required')],"
        " 'body': [ErrorDetail(string='This field is required.', code='required')]}]."
    )
    assert str(exc_info.value) == expected_error_message


def test_get_initial_data_client_error(
    remote_posts_api: RemoteModelAPI, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=remote_posts_api.client.base_url,
        status_code=500,
    )
    with pytest.raises(RemoteAPIError) as exc_info:
        remote_posts_api.get_initial_data()
    expected_error_message = (
        "An error occurred while requesting URL('http://test/blog'): "
        "Server error '500 Internal Server Error' for url 'http://test/blog'\n"
        "For more information check: "
        "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/500"
    )
    assert str(exc_info.value) == expected_error_message


def test_sync_created(
    remote_posts_api: RemoteModelAPI, httpx_mock: HTTPXMock, test_post: Post
) -> None:
    response_data = RemotePostSerializer(test_post).data
    httpx_mock.add_response(
        method="POST",
        url=remote_posts_api.client.base_url,
        json=response_data,
        status_code=201,
    )
    remote_posts_api.sync_created([test_post])


def test_sync_updated(
    remote_posts_api: RemoteModelAPI, httpx_mock: HTTPXMock, test_post: Post
) -> None:
    response_data = RemotePostSerializer(test_post).data
    httpx_mock.add_response(
        method="PUT",
        url=remote_posts_api.client.get_detail_url(test_post.id),
        json=response_data,
        status_code=200,
    )
    remote_posts_api.sync_updated([test_post])


def test_sync_deleted(
    remote_posts_api: RemoteModelAPI, httpx_mock: HTTPXMock, test_post: Post
) -> None:
    httpx_mock.add_response(
        method="DELETE",
        url=remote_posts_api.client.get_detail_url(test_post.id),
        status_code=204,
    )
    remote_posts_api.sync_deleted([test_post])


@pytest.mark.parametrize("method", ["create", "delete", "update"])
def test__sync(
    remote_posts_api: RemoteModelAPI,
    httpx_mock: HTTPXMock,
    test_post: Post,
    method: str,
) -> None:
    response_data = [] if method == "delete" else RemotePostSerializer(test_post).data
    url = (
        remote_posts_api.client.base_url
        if method == "create"
        else remote_posts_api.client.get_detail_url(test_post.id)
    )
    httpx_mock.add_response(
        url=url,
        json=response_data,
        status_code=200,
    )
    synced_models, errors = remote_posts_api._sync(method, [test_post])  # noqa: SLF001
    assert len(synced_models) == 1
    assert len(errors) == 0


def test__sync_invalid_method(
    remote_posts_api: RemoteModelAPI,
    httpx_mock: HTTPXMock,
    test_post: Post,
) -> None:
    with pytest.raises(RemoteAPIError) as exc_info:
        remote_posts_api._sync("invalid_method", [test_post])  # noqa: SLF001
    expected_error_message = (
        "Error syncronazing Posts: " "invalid_method is not a valid method name"
    )
    assert str(exc_info.value) == expected_error_message


def test__sync_client_error(
    remote_posts_api: RemoteModelAPI,
    httpx_mock: HTTPXMock,
    test_post: Post,
) -> None:
    httpx_mock.add_response(
        url=remote_posts_api.client.base_url,
        status_code=500,
    )
    _, errors = remote_posts_api._sync("create", [test_post])  # noqa: SLF001
    assert len(errors) == 1
    instance, exc = errors[0]
    assert instance == test_post
    assert isinstance(exc, HTTPStatusError)
    expected_error_message = "Server error '500 Internal Server Error'"
    assert expected_error_message in str(exc)
