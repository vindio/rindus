import pytest
from django.urls import reverse
from rest_framework import status

from blog.models import Comment
from blog.models import Post
from blog.tests.factories import CommentFactory
from blog.tests.factories import PostFactory


@pytest.mark.django_db()
def test_create_comment_requires_auth(api_client) -> None:
    url = reverse("api:comment-list")
    response = api_client.post(url, format="json")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db()
def test_create_comment(api_authorized_client) -> None:
    post = PostFactory()
    assert type(post) is Post
    comment_list_url = reverse("api:comment-list")
    payload = {
        "post": post.id,
        "name": "id labore ex et quam laborum",
        "email": "Eliseo@gardner.biz",
        "body": "laudantium enim quasi",
    }
    response = api_authorized_client.post(comment_list_url, data=payload, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    assert "id" in response.data
    created_comment_id = response.data["id"]
    assert response.data["name"] == payload["name"]
    assert response.data["email"] == payload["email"]
    assert response.data["body"] == payload["body"]
    assert Comment.objects.filter(
        id=created_comment_id,
        post=post,
        name=payload["name"],
        email=payload["email"],
        body=payload["body"],
    ).exists()


@pytest.mark.django_db()
def test_retrieve_comment_requires_auth(api_client) -> None:
    url = reverse("api:comment-detail", kwargs={"pk": 1})
    response = api_client.get(url, format="json")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db()
def test_retrieve_comment(api_authorized_client) -> None:
    comment = CommentFactory()
    assert type(comment) is Comment
    url = reverse("api:comment-detail", kwargs={"pk": comment.id})
    response = api_authorized_client.get(url, format="json")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == comment.id
    assert response.data["post"] == comment.post_id
    assert response.data["name"] == comment.name
    assert response.data["email"] == comment.email
    assert response.data["body"] == comment.body


@pytest.mark.django_db()
def test_retrieve_comment_list_requires_auth(api_client) -> None:
    url = reverse("api:comment-list")
    response = api_client.get(url, format="json")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db()
def test_retrieve_comment_list(api_authorized_client) -> None:
    comment_list_url = reverse("api:comment-list")
    num_comments = 2
    comments = CommentFactory.create_batch(num_comments)
    response = api_authorized_client.get(comment_list_url, format="json")
    assert response.data.get("count") == num_comments
    assert len(response.data.get("results")) == num_comments
    # NOTE: Depends on comments ordering
    for i, comment in enumerate(response.data.get("results")):
        assert comments[i].id == comment["id"]
        assert comments[i].post_id == comment["post"]
        assert comments[i].name == comment["name"]
        assert comments[i].email == comment["email"]
        assert comments[i].body == comment["body"]


@pytest.mark.django_db()
def test_put_comment_requires_auth(api_client) -> None:
    url = reverse("api:comment-detail", kwargs={"pk": 1})
    response = api_client.put(url, format="json")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db()
def test_put_comment(api_authorized_client) -> None:
    comment = CommentFactory()
    new_post = PostFactory()
    assert type(comment) is Comment
    assert type(new_post) is Post
    payload = {
        "post": new_post.id,
        "name": "new_name",
        "email": "new@email.test",
        "body": "new body",
    }
    url = reverse("api:comment-detail", kwargs={"pk": comment.id})
    response = api_authorized_client.put(url, data=payload, format="json")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == comment.id
    assert response.data["post"] == payload["post"]
    assert response.data["name"] == payload["name"]
    assert response.data["email"] == payload["email"]
    assert response.data["body"] == payload["body"]
    comment.refresh_from_db()
    assert comment.post == new_post
    assert comment.name == payload["name"]
    assert comment.email == payload["email"]
    assert comment.body == payload["body"]


@pytest.mark.django_db()
def test_patch_comment_requires_auth(api_client) -> None:
    url = reverse("api:comment-detail", kwargs={"pk": 1})
    response = api_client.patch(url, format="json")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize(
    ("field_name", "value"),
    [("name", "new name"), ("email", "new_email@test.me"), ("body", "new body")],
)
@pytest.mark.django_db()
def test_patch_patch_single_field(
    api_authorized_client, field_name: str, value: str
) -> None:
    comment = CommentFactory()
    assert type(comment) is Comment
    payload = {field_name: value}
    url = reverse("api:comment-detail", kwargs={"pk": comment.id})
    response = api_authorized_client.patch(url, data=payload, format="json")
    assert response.status_code == status.HTTP_200_OK
    assert response.data[field_name] == value
    comment.refresh_from_db()
    assert getattr(comment, field_name) == value


@pytest.mark.django_db()
def test_comment_update_post(api_authorized_client) -> None:
    comment = CommentFactory()
    post = PostFactory()
    assert type(comment) is Comment
    assert type(post) is Post
    payload = {"post": post.id}
    url = reverse("api:comment-detail", kwargs={"pk": comment.id})
    response = api_authorized_client.patch(url, data=payload, format="json")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["post"] == post.id
    comment.refresh_from_db()
    assert comment.post == post


@pytest.mark.django_db()
def test_delete_comment_requires_auth(api_client) -> None:
    url = reverse("api:comment-detail", kwargs={"pk": 1})
    response = api_client.delete(url, format="json")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db()
def test_delete_post(api_authorized_client) -> None:
    comment = CommentFactory()
    assert type(comment) is Comment
    url = reverse("api:comment-detail", kwargs={"pk": comment.id})
    response = api_authorized_client.delete(url, format="json")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Comment.objects.filter(id=comment.id).exists()
