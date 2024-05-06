import httpx
import pytest
from django.db.utils import IntegrityError
from pytest_httpx import HTTPXMock

from blog.models import Comment
from blog.models import Post
from blog.remote_api import LoadRemoteDataError
from blog.remote_api import _load_data
from blog.remote_api import load_comments
from blog.remote_api import load_initial_data
from blog.remote_api import load_posts
from blog.remote_api import update_sequences
from blog.serializers import RemotePostSerializer


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_load_initia_data(
    httpx_mock: HTTPXMock,
    api_urls,
    django_assert_num_queries,
    posts_response,
    comments_response,
):
    httpx_mock.add_response(
        method="GET", url=api_urls["posts"], json=posts_response, status_code=200
    )
    httpx_mock.add_response(
        method="GET", url=api_urls["comments"], json=comments_response, status_code=200
    )
    expected_queries = """Expected queries:
[1] BEGIN
[2] SAVEPOINT ...
[3] INSERT INTO "blog_post" ("id", "user_id", "title", "body") VALUES ...
[4] INSERT INTO "blog_comment" ("id", "post_id", "name", "email", "body") VALUES ...
[5] RELEASE SAVEPOINT ...
[6] SELECT setval(pg_get_serial_sequence('"blog_post"','id'), ...
[7] SELECT setval(pg_get_serial_sequence('"blog_comment"','id'), ...
[8] COMMIT
"""
    num_expected_posts = 2
    num_expected_comments = 2
    with django_assert_num_queries(8, info=expected_queries):
        num_loaded_posts, num_loaded_comments = load_initial_data(
            api_urls["posts"], api_urls["comments"]
        )
        assert num_loaded_posts == num_expected_posts
        assert num_loaded_comments == num_expected_comments
    # Loaded data is saved on database
    assert Post.objects.count() == num_expected_posts
    assert Comment.objects.count() == num_expected_comments


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_load_posts(httpx_mock: HTTPXMock, posts_response):
    expected_num_loaded_posts = 2
    headers = {
        "Content-type": "application/json; charset=UTF-8",
    }
    httpx_mock.add_response(
        method="GET", url="http://posts", json=posts_response, status_code=200
    )
    with httpx.Client(headers=headers) as client:
        num_loaded_posts = load_posts(client, "http://posts")
    assert num_loaded_posts == expected_num_loaded_posts
    assert Post.objects.count() == expected_num_loaded_posts


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_load_comments(httpx_mock: HTTPXMock, first_post, comments_response):
    expected_num_loaded_comments = 2
    headers = {
        "Content-type": "application/json; charset=UTF-8",
    }
    httpx_mock.add_response(
        method="GET", url="http://comments", json=comments_response, status_code=200
    )
    with httpx.Client(headers=headers) as client:
        num_loaded_comments = load_comments(client, "http://comments")
    assert num_loaded_comments == expected_num_loaded_comments
    assert Comment.objects.count() == expected_num_loaded_comments
    assert first_post.comments.count() == expected_num_loaded_comments


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_update_sequences():
    for i in range(3):
        Post.objects.create(id=i + 1, user_id=1, title=f"title_{i}", body=f"body {i}")
    with pytest.raises(IntegrityError) as exc_info:
        Post.objects.create(user_id=1, title="title_last", body="body last")
    expected_error = 'duplicate key value violates unique constraint "blog_post_pkey"'
    expected_error_detail = "Key (id)=(1) already exists."
    exception_message = str(exc_info.value)
    assert expected_error in exception_message
    assert expected_error_detail in exception_message
    update_sequences([Post])
    post = Post.objects.create(user_id=1, title="title_last", body="body last")
    expected_id = 4
    assert post.pk == expected_id


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_load_data_validation_error(httpx_mock: HTTPXMock):
    headers = {
        "Content-type": "application/json; charset=UTF-8",
    }
    posts_url = "http://posts"
    httpx_mock.add_response(
        method="GET",
        url=posts_url,
        json=[{"id": 1, "userId": 1, "title": "title 1"}],
        status_code=200,
    )
    with (
        pytest.raises(LoadRemoteDataError) as exc_info,
        httpx.Client(headers=headers) as client,
    ):
        _load_data(client, posts_url, Post, RemotePostSerializer)
    expected_error = (
        "Error loading posts: "
        "[{'body': [ErrorDetail(string='This field is required.', code='required')]}]."
    )
    assert str(exc_info.value) == expected_error


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_load_initial_data_db_error(httpx_mock: HTTPXMock, posts_response, first_post):
    posts_url = "http://posts"
    httpx_mock.add_response(
        method="GET",
        url=posts_url,
        json=posts_response,
        status_code=200,
    )
    used_id = 1
    assert first_post.id == used_id
    with (
        pytest.raises(LoadRemoteDataError) as exc_info,
    ):
        load_initial_data(posts_url, "http://commments")
    expected_error = (
        "An error occurred saving data: "
        'duplicate key value violates unique constraint "blog_post_pkey"'
        f"\nDETAIL:  Key (id)=({used_id}) already exists."
    )
    assert str(exc_info.value) == expected_error
