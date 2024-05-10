from io import StringIO
from unittest.mock import patch

import httpx
import pytest
from django.core.management import CommandError
from django.core.management import call_command
from pytest_httpx import HTTPXMock

from blog.management.commands.sync_remote_data import sync_remote_data
from blog.management.commands.sync_remote_data import update_synced_models
from blog.managers import SyncStatus
from blog.models import Comment
from blog.models import Post
from blog.remote_api import RemoteAPIError
from blog.serializers import RemotePostSerializer
from blog.sync_reports import SyncBlogReport
from blog.sync_reports import SyncModelReport
from blog.tests.factories import CommentFactory
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
def test_command_sync_remote_data_args(
    posts_url: str | None,
    comments_url: str | None,
) -> None:
    default_posts_url = "https://jsonplaceholder.typicode.com/posts"
    default_comments_url = "https://jsonplaceholder.typicode.com/comments"
    args = []
    if posts_url:
        args.append(f"--posts-url={posts_url}")
    if comments_url:
        args.append(f"--comments-url={comments_url}")
    expected_posts_url = posts_url or default_posts_url
    expected_comments_url = comments_url or default_comments_url
    with patch("blog.management.commands.sync_remote_data.sync_remote_data") as mock:
        call_command("sync_remote_data", args)
    mock.assert_called_once()
    expected_num_args = 3
    assert len(mock.call_args.args) == expected_num_args
    post_url_arg = mock.call_args.args[1]
    comments_url_arg = mock.call_args.args[2]
    assert post_url_arg == expected_posts_url
    assert comments_url_arg == expected_comments_url


@pytest.mark.django_db(transaction=True)
def test_command_sync_remote_data(api_urls: dict[str, str]) -> None:
    output = StringIO()
    call_command("sync_remote_data", stdout=output)
    expected_output_lines = (
        "Successfully synced posts and comments.",
        "posts (created=0, updated=0, deleted=0)",
        "comments (created=0, updated=0, deleted=0)",
    )
    for line in expected_output_lines:
        assert line in output.getvalue()


@pytest.mark.django_db(transaction=True)
def test_command_sync_remote_data_error(api_urls: dict[str, str]) -> None:
    expected_error_message = "Unespected error!"
    with (
        patch(
            "blog.management.commands.sync_remote_data.sync_remote_data",
            side_effect=RemoteAPIError(expected_error_message),
        ) as mock,
        pytest.raises(CommandError) as exc_info,
    ):
        call_command("sync_remote_data")
    mock.assert_called_once()
    assert str(exc_info.value) == expected_error_message


@pytest.mark.django_db(transaction=True)
def test_command_sync_remote_data_syncs_new_instances(
    httpx_mock: HTTPXMock, httpx_client: httpx.Client, api_urls: dict[str, str]
) -> None:
    post = PostFactory.create()
    assert post.status == SyncStatus.CREATED
    httpx_mock.add_response(
        method="POST",
        url=api_urls["posts"],
        json=RemotePostSerializer(post).data,
        status_code=201,
    )
    report = sync_remote_data(httpx_client, api_urls["posts"], api_urls["comments"])
    assert report.posts.created == 1
    post.refresh_from_db()
    assert post.status == SyncStatus.SYNCED


@pytest.mark.django_db(transaction=True)
def test_command_sync_remote_data_does_not_syncs_new_instances_status_if_error(
    httpx_mock: HTTPXMock, httpx_client: httpx.Client, api_urls: dict[str, str]
) -> None:
    post = PostFactory.create()
    assert post.status == SyncStatus.CREATED
    httpx_mock.add_response(
        method="POST",
        url=api_urls["posts"],
        status_code=500,
    )
    report = sync_remote_data(httpx_client, api_urls["posts"], api_urls["comments"])
    assert report.posts.created == 0
    assert report.posts.num_errors == 1
    post.refresh_from_db()
    assert post.status == SyncStatus.CREATED


@pytest.mark.django_db(transaction=True)
def test_command_sync_remote_data_syncs_modified_instances(
    httpx_mock: HTTPXMock, httpx_client: httpx.Client, api_urls: dict[str, str]
) -> None:
    post = PostFactory.build(status=SyncStatus.UPDATED)
    Post.objects.bulk_create([post])
    post.refresh_from_db()
    assert post.status == SyncStatus.UPDATED
    httpx_mock.add_response(
        method="PUT",
        url=api_urls["posts"] + f"/{post.id}",
        json=RemotePostSerializer(post).data,
        status_code=201,
    )
    report = sync_remote_data(httpx_client, api_urls["posts"], api_urls["comments"])
    assert report.posts.updated == 1
    post.refresh_from_db()
    assert post.status == SyncStatus.SYNCED


@pytest.mark.django_db(transaction=True)
def test_command_sync_remote_data_does_not_syncs_modified_instances_status_if_error(
    httpx_mock: HTTPXMock, httpx_client: httpx.Client, api_urls: dict[str, str]
) -> None:
    post = PostFactory.build(status=SyncStatus.UPDATED)
    Post.objects.bulk_create([post])
    post.refresh_from_db()
    assert post.status == SyncStatus.UPDATED
    httpx_mock.add_response(
        method="PUT",
        url=api_urls["posts"] + f"/{post.id}",
        status_code=500,
    )
    report = sync_remote_data(httpx_client, api_urls["posts"], api_urls["comments"])
    assert report.posts.updated == 0
    assert report.posts.num_errors == 1
    post.refresh_from_db()
    assert post.status == SyncStatus.UPDATED


@pytest.mark.django_db(transaction=True)
def test_command_sync_remote_data_syncs_deleted_instances(
    httpx_mock: HTTPXMock, httpx_client: httpx.Client, api_urls: dict[str, str]
) -> None:
    post = PostFactory.build(status=SyncStatus.DELETED)
    Post.objects.bulk_create([post])
    post.refresh_from_db()
    assert post.status == SyncStatus.DELETED
    httpx_mock.add_response(
        method="DELETE",
        url=api_urls["posts"] + f"/{post.id}",
        status_code=204,
    )
    report = sync_remote_data(httpx_client, api_urls["posts"], api_urls["comments"])
    assert report.posts.deleted == 1
    assert not Post.all_objects.filter(id=post.id).exists()


@pytest.mark.django_db(transaction=True)
def test_command_sync_remote_data_does_not_delete_deleted_instances_if_error(
    httpx_mock: HTTPXMock, httpx_client: httpx.Client, api_urls: dict[str, str]
) -> None:
    post = PostFactory.build(status=SyncStatus.DELETED)
    Post.objects.bulk_create([post])
    post.refresh_from_db()
    assert post.status == SyncStatus.DELETED
    httpx_mock.add_response(
        method="DELETE",
        url=api_urls["posts"] + f"/{post.id}",
        status_code=500,
    )
    report = sync_remote_data(httpx_client, api_urls["posts"], api_urls["comments"])
    assert report.posts.deleted == 0
    assert report.posts.num_errors == 1
    assert Post.deleted.filter(id=post.id).exists()
    post.refresh_from_db()
    assert post.status == SyncStatus.DELETED


@pytest.mark.parametrize(
    ("created", "updated", "deleted", "errors", "expected_output"),
    [
        (
            0,
            0,
            0,
            [],
            (
                "Successfully synced posts and comments.",
                "posts (created=0, updated=0, deleted=0)",
                "comments (created=0, updated=0, deleted=0)",
            ),
        ),
        (
            0,
            0,
            0,
            ["err"],
            (
                "ERROR SYNCRONIZANDO posts (num_errors=1)",
                "err",
                "Successfully synced Comments.",
                "posts (created=0, updated=0, deleted=0)",
            ),
        ),
        (
            1,
            0,
            0,
            [],
            (
                "Successfully synced posts and comments.",
                "posts (created=1, updated=0, deleted=0)",
                "comments (created=0, updated=0, deleted=0)",
            ),
        ),
        (
            1,
            0,
            0,
            ["err"],
            (
                "PARTIAL posts SYNC",
                "err",
                "Successfully synced Comments.",
                "posts (created=0, updated=0, deleted=0)",
            ),
        ),
        (
            0,
            1,
            0,
            [],
            (
                "Successfully synced posts and comments.",
                "posts (created=0, updated=1, deleted=0)",
                "comments (created=0, updated=0, deleted=0)",
            ),
        ),
        (
            0,
            1,
            0,
            ["err"],
            (
                "PARTIAL posts SYNC",
                "err",
                "Successfully synced Comments.",
                "posts (created=0, updated=0, deleted=0)",
            ),
        ),
        (
            0,
            0,
            1,
            [],
            (
                "Successfully synced posts and comments.",
                "posts (created=0, updated=0, deleted=1)",
                "comments (created=0, updated=0, deleted=0)",
            ),
        ),
        (
            0,
            0,
            1,
            ["err"],
            (
                "PARTIAL posts SYNC",
                "err",
                "Successfully synced Comments.",
                "posts (created=0, updated=0, deleted=0)",
            ),
        ),
    ],
)
def test_process_report(
    created: int,
    updated: int,
    deleted: int,
    errors: list[str],
    expected_output: tuple[str],
) -> None:
    output = StringIO()
    posts_report = SyncModelReport(created, updated, deleted, errors)
    comments_report = SyncModelReport(0, 0, 0, [])
    blog_report = SyncBlogReport(posts_report, comments_report)
    with patch(
        "blog.management.commands.sync_remote_data.sync_remote_data",
        return_value=blog_report,
    ) as mock:
        call_command("sync_remote_data", stdout=output)
    mock.assert_called_once()
    for line in expected_output:
        assert line in output.getvalue()


@pytest.mark.django_db(transaction=True)
def test_update_synced_models() -> None:
    post_updated = PostFactory.build(status=SyncStatus.UPDATED)
    post_deleted = PostFactory.build(status=SyncStatus.DELETED)
    Post.objects.bulk_create([post_updated, post_deleted])
    comment_updated = CommentFactory.build(status=SyncStatus.UPDATED, post=post_updated)
    comment_deleted = CommentFactory.build(status=SyncStatus.DELETED, post=post_updated)
    Comment.objects.bulk_create([comment_updated, comment_deleted])
    update_synced_models(
        [post_updated], [post_deleted], [comment_updated], [comment_deleted]
    )
    assert not Post.all_objects.filter(id=post_deleted.id).exists()
    assert not Comment.all_objects.filter(id=comment_deleted.id).exists()
    post_updated.refresh_from_db()
    assert post_updated.status == SyncStatus.SYNCED
    comment_updated.refresh_from_db()
    assert comment_updated.status == SyncStatus.SYNCED
