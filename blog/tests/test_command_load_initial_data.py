from io import StringIO
from unittest.mock import patch

import httpx
import pytest
from django.core.management import CommandError
from django.core.management import call_command
from django.db.utils import IntegrityError
from pytest_httpx import HTTPXMock

from blog.management.commands.load_initial_data import load_initial_data
from blog.management.commands.load_initial_data import load_model
from blog.management.commands.load_initial_data import update_sequences
from blog.models import Comment
from blog.models import Post
from blog.remote_api import RemoteAPIError
from blog.serializers import RemotePostSerializer
from blog.tests.factories import PostFactory


@pytest.mark.parametrize(
    ("posts_url", "comments_url"),
    [
        (None, None),
        ("http://posts", None),
        ("http://posts_url", "http://comments_url"),
        (None, "http://comments_url"),
    ],
)
def test_command_load_initial_data_args(
    posts_url: str | None, comments_url: str | None
) -> None:
    default_posts_url = "https://jsonplaceholder.typicode.com/posts"
    default_comments_url = "https://jsonplaceholder.typicode.com/comments"
    args = []
    if posts_url:
        args.append(f"--posts-url={posts_url}")
    if comments_url:
        args.append(f"--comments-url={comments_url}")
    with patch(
        "blog.management.commands.load_initial_data.load_initial_data",
        return_value=([], []),
    ) as mock:
        call_command("load_initial_data", args)
    expected_num_args = 3
    mock.assert_called_once()
    assert len(mock.call_args.args) == expected_num_args
    post_url_arg = mock.call_args.args[1]
    comments_url_arg = mock.call_args.args[2]
    expected_posts_url = posts_url or default_posts_url
    assert post_url_arg == expected_posts_url
    expected_comments_url = comments_url or default_comments_url
    assert comments_url_arg == expected_comments_url


@pytest.mark.django_db(transaction=True)
def test_command_load_initial_data_error(httpx_mock: HTTPXMock) -> None:
    output = StringIO()
    num_expected_posts = num_expected_comments = 0
    expected_output = "ERROR"

    httpx_mock.add_exception(httpx.ReadTimeout("Unable to read within timeout"))
    expected_output = (
        "An error occurred while requesting URL('http://posts.test'): "
        "Unable to read within timeout"
    )
    with pytest.raises(CommandError) as exc_info:
        call_command("load_initial_data", posts_url="http://posts.test", stdout=output)
    assert str(exc_info.value) == expected_output
    # Loaded data is NOT saved on database
    assert Post.objects.count() == num_expected_posts
    assert Comment.objects.count() == num_expected_comments


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_command_load_initial_data(
    httpx_mock: HTTPXMock,
    api_urls: dict[str, str],
    posts_response: dict,
    comments_response: dict,
) -> None:
    num_expected_posts = num_expected_comments = 2
    expected_output = (
        f"Successfully loaded {num_expected_posts} posts "
        f"and {num_expected_comments} comments."
    )
    output = StringIO()
    args = (
        f"--posts-url={api_urls['posts']}",
        f"--comments-url={api_urls['comments']}",
    )

    httpx_mock.add_response(
        method="GET", url=api_urls["posts"], json=posts_response, status_code=200
    )
    httpx_mock.add_response(
        method="GET", url=api_urls["comments"], json=comments_response, status_code=200
    )
    call_command("load_initial_data", args, stdout=output)
    assert expected_output in output.getvalue()
    # Loaded data is saved on database
    assert Post.objects.count() == num_expected_posts
    assert Comment.objects.count() == num_expected_comments
    assert Post.objects.synced().count() == num_expected_posts
    assert Comment.objects.synced().count() == num_expected_comments


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_load_data_validation_error(httpx_mock: HTTPXMock) -> None:
    posts_url = "http://posts"
    httpx_mock.add_response(
        method="GET",
        url=posts_url,
        json=[{"id": 1, "userId": 1, "title": "title 1"}],
        status_code=200,
    )
    with (
        pytest.raises(RemoteAPIError) as exc_info,
        httpx.Client() as client,
    ):
        load_model(client, posts_url, "Posts", RemotePostSerializer)
    expected_error = (
        "Error loading Posts: "
        "[{'body': [ErrorDetail(string='This field is required.', code='required')]}]."
    )
    assert str(exc_info.value) == expected_error


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_update_sequences() -> None:
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
def test_load_initial_data_db_error(
    httpx_mock: HTTPXMock, posts_response: dict
) -> None:
    first_post = PostFactory(id=1)
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
        pytest.raises(RemoteAPIError) as exc_info,
        httpx.Client() as client,
    ):
        load_initial_data(client, posts_url, "http://commments")
    expected_error = (
        "An error occurred saving data: "
        'duplicate key value violates unique constraint "blog_post_pkey"'
        f"\nDETAIL:  Key (id)=({used_id}) already exists."
    )
    assert str(exc_info.value) == expected_error


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_load_initia_data(
    httpx_mock: HTTPXMock,
    api_urls: dict[str, str],
    django_assert_num_queries,
    posts_response: dict,
    comments_response: dict,
) -> None:
    httpx_mock.add_response(
        method="GET", url=api_urls["posts"], json=posts_response, status_code=200
    )
    httpx_mock.add_response(
        method="GET", url=api_urls["comments"], json=comments_response, status_code=200
    )
    expected_queries = """Expected queries:
[1] BEGIN
[2] INSERT INTO "blog_post" ("id", "user_id", "title", "body") VALUES ...
[3] INSERT INTO "blog_comment" ("id", "post_id", "name", "email", "body") VALUES ...
[4] SELECT setval(pg_get_serial_sequence('"blog_post"','id'), ...
[5] SELECT setval(pg_get_serial_sequence('"blog_comment"','id'), ...
[6] UPDATE "blog_post" SET "status"...
[7] UPDATE "blog_comment" SET "status"...
[8] COMMIT
"""
    num_expected_posts = 2
    num_expected_comments = 2
    with django_assert_num_queries(8, info=expected_queries):
        with httpx.Client() as client:
            loaded_posts, loaded_comments = load_initial_data(
                client, api_urls["posts"], api_urls["comments"]
            )
        assert len(loaded_posts) == num_expected_posts
        assert len(loaded_comments) == num_expected_comments
    # Loaded data is saved on database
    assert Post.objects.count() == num_expected_posts
    assert Comment.objects.count() == num_expected_comments
    # Loaded data status == SYNCED
    assert Post.objects.synced().count() == num_expected_posts
    assert Comment.objects.synced().count() == num_expected_comments
