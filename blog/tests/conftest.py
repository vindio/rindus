import pytest

from blog.models import Post


@pytest.fixture()
def first_post() -> Post:
    return Post.objects.create(
        id=1,
        user_id=1,
        title="sunt aut facere repellat",
        body="quia et suscipit",
    )


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
