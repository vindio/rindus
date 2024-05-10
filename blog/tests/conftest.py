import httpx
import pytest
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from blog.remote_api import JSONAPIClient

User = get_user_model()


@pytest.fixture()
def api_user():
    return User.objects.create()


@pytest.fixture()
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture()
def api_authorized_client(api_user, api_client: APIClient) -> APIClient:
    token, _ = Token.objects.get_or_create(user=api_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.key}")
    return api_client


@pytest.fixture()
def httpx_client() -> httpx.Client:
    return httpx.Client()


@pytest.fixture()
def json_api_client(httpx_client: httpx.Client) -> JSONAPIClient:
    return JSONAPIClient(httpx_client, "http://test/blog")


@pytest.fixture()
def api_urls() -> dict[str, str]:
    return {"posts": "https://posts_url", "comments": "https://comments_url"}


@pytest.fixture()
def posts_response() -> list[dict[str, int | str]]:
    return [
        {
            "userId": 1,
            "id": 1,
            "title": "sunt aut facere repellat",
            "body": "quia et suscipit",
        },
        {
            "userId": 1,
            "id": 2,
            "title": "qui est esse",
            "body": "est rerum tempore vitae",
        },
    ]


@pytest.fixture()
def comments_response() -> list[dict[str, int | str]]:
    return [
        {
            "postId": 1,
            "id": 1,
            "name": "id labore ex et quam laborum",
            "email": "Eliseo@gardner.biz",
            "body": "laudantium enim quasi",
        },
        {
            "postId": 1,
            "id": 2,
            "name": "quo vero reiciendis velit similique earum",
            "email": "Jayne_Kuhic@sydney.com",
            "body": "est natus enim nihil est dolore omnis voluptatem numquam",
        },
    ]
