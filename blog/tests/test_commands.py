from io import StringIO

import httpx
import pytest
from django.core.management import CommandError
from django.core.management import call_command
from pytest_httpx import HTTPXMock

from blog.models import Comment
from blog.models import Post


@pytest.mark.django_db(transaction=True, reset_sequences=True)
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
    posts_url: str | None, comments_url: str | None, httpx_mock: HTTPXMock
):
    default_posts_url = "https://jsonplaceholder.typicode.com/posts"
    default_comments_url = "https://jsonplaceholder.typicode.com/comments"
    posts_url_arg = posts_url or default_posts_url
    comments_url_arg = comments_url or default_comments_url
    httpx_mock.add_response(method="GET", url=posts_url_arg, json=[], status_code=200)
    httpx_mock.add_response(
        method="GET", url=comments_url_arg, json=[], status_code=200
    )
    args = []
    if posts_url:
        args.append(f"--posts-url={posts_url}")
    if comments_url:
        args.append(f"--comments-url={comments_url}")
    call_command("load_initial_data", args)


@pytest.mark.django_db(transaction=True)
def test_command_load_initial_data_error(httpx_mock: HTTPXMock):
    output = StringIO()
    num_expected_posts = num_expected_comments = 0
    expected_output = "ERROR"

    httpx_mock.add_exception(httpx.ReadTimeout("Unable to read within timeout"))
    expected_output = (
        "An error occurred while requesting URL('http://posts.test').: "
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
    api_urls,
    posts_response,
    comments_response,
):
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
