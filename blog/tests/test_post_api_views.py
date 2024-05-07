import pytest
from django.urls import reverse
from rest_framework import status

from blog.models import DEFAULT_USER_ID
from blog.models import Post
from blog.tests.factories import PostFactory


@pytest.mark.django_db()
def test_create_post_requires_auth(api_client) -> None:
    url = reverse("api:post-list")
    response = api_client.post(url, format="json")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db()
def test_create_post(api_authorized_client) -> None:
    url = reverse("api:post-list")
    payload = {
        "title": "sunt aut facere repellat",
        "body": "quia et suscipit",
    }
    response = api_authorized_client.post(url, data=payload, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    assert "id" in response.data
    created_post_id = response.data["id"]
    assert response.data["user_id"] == DEFAULT_USER_ID
    assert response.data["title"] == payload["title"]
    assert response.data["body"] == payload["body"]
    assert Post.objects.filter(
        id=created_post_id,
        user_id=DEFAULT_USER_ID,
        title=payload["title"],
        body=payload["body"],
    ).exists()


@pytest.mark.django_db()
def test_retrieve_post_requires_auth(api_client) -> None:
    url = reverse("api:post-detail", kwargs={"pk": 1})
    response = api_client.get(url, format="json")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db()
def test_retrieve_post(api_authorized_client) -> None:
    post = PostFactory()
    assert type(post) is Post
    url = reverse("api:post-detail", kwargs={"pk": post.id})
    response = api_authorized_client.get(url, format="json")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == post.id
    assert response.data["user_id"] == post.user_id
    assert response.data["title"] == post.title
    assert response.data["body"] == post.body


@pytest.mark.django_db()
def test_retrieve_post_list_requires_auth(api_client) -> None:
    url = reverse("api:post-list")
    response = api_client.get(url, format="json")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db()
def test_retrieve_post_list(api_authorized_client) -> None:
    url = reverse("api:post-list")
    num_posts = 3
    posts = PostFactory.create_batch(num_posts)
    response = api_authorized_client.get(url, format="json")
    assert response.data.get("count") == num_posts
    assert len(response.data.get("results")) == num_posts
    # NOTE: Depends on posts ordering
    for i, post in enumerate(response.data.get("results")):
        assert posts[i].id == post["id"]
        assert posts[i].user_id == post["user_id"]
        assert posts[i].title == post["title"]
        assert posts[i].body == post["body"]


@pytest.mark.django_db()
def test_put_post_requires_auth(api_client) -> None:
    url = reverse("api:post-list")
    response = api_client.put(url, format="json")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db()
def test_put_post(api_authorized_client) -> None:
    post = PostFactory()
    assert type(post) is Post
    payload = {
        "title": "new title",
        "body": "new body",
        "user_id": 33,  # Different from DEFAULT_USER_ID
    }
    url = reverse("api:post-detail", kwargs={"pk": post.id})
    response = api_authorized_client.put(url, data=payload, format="json")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == post.id
    assert response.data["user_id"] == DEFAULT_USER_ID  # NOT CHANGED
    assert response.data["title"] == payload["title"]
    assert response.data["body"] == payload["body"]
    post.refresh_from_db()
    assert post.user_id == DEFAULT_USER_ID  # NOT CHANGED
    assert post.title == payload["title"]
    assert post.body == payload["body"]


@pytest.mark.django_db()
def test_patch_post_requires_auth(api_client) -> None:
    url = reverse("api:post-list")
    response = api_client.patch(url, format="json")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db()
def test_patch_post_title(api_authorized_client) -> None:
    post = PostFactory()
    assert type(post) is Post
    payload = {
        "title": "new title",
    }
    url = reverse("api:post-detail", kwargs={"pk": post.id})
    response = api_authorized_client.patch(url, data=payload, format="json")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["title"] == payload["title"]
    post.refresh_from_db()
    assert post.title == payload["title"]


@pytest.mark.django_db()
def test_patch_post_body(api_authorized_client) -> None:
    post = PostFactory()
    assert type(post) is Post
    payload = {
        "body": "new body",
    }
    url = reverse("api:post-detail", kwargs={"pk": post.id})
    response = api_authorized_client.patch(url, data=payload, format="json")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["body"] == payload["body"]
    post.refresh_from_db()
    assert post.body == payload["body"]


@pytest.mark.django_db()
def test_patch_post_user_id_not_allowed(api_authorized_client) -> None:
    post = PostFactory()
    assert type(post) is Post
    payload = {
        "user_id": 33,  # Different from DEFAULT_USER_ID
    }
    url = reverse("api:post-detail", kwargs={"pk": post.id})
    response = api_authorized_client.patch(url, data=payload, format="json")
    # NOTE: DRF DOES NOT RETURN 400 BAD REQUEST
    # https://github.com/encode/django-rest-framework/issues/1655
    assert response.status_code == status.HTTP_200_OK
    assert response.data["user_id"] == DEFAULT_USER_ID  # NOT CHANGED
    post.refresh_from_db()
    assert post.user_id == DEFAULT_USER_ID


@pytest.mark.django_db()
def test_delete_post_requires_auth(api_client) -> None:
    url = reverse("api:post-detail", kwargs={"pk": 1})
    response = api_client.delete(url, format="json")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db()
def test_delete_post(api_authorized_client) -> None:
    post = PostFactory()
    assert type(post) is Post
    url = reverse("api:post-detail", kwargs={"pk": post.id})
    response = api_authorized_client.delete(url, format="json")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Post.objects.filter(id=post.id).exists()
