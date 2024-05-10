from collections import namedtuple
from collections.abc import Iterable

import httpx
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import models

from blog.models import Comment
from blog.models import Post
from blog.models import set_status_to_synced
from blog.remote_api import JSONAPIClient
from blog.remote_api import RemoteAPIError
from blog.remote_api import RemoteModelAPI
from blog.serializers import RemoteCommentSerializer
from blog.serializers import RemotePostSerializer
from blog.sync_reports import SyncBlogReport
from blog.sync_reports import SyncModelReport

SyncResult = namedtuple("SyncResult", ("instances", "errors"))  # noqa: PYI024


def make_error_messages(
    errors: list[tuple[models.Model, Exception]], action: str
) -> list[str]:
    return [
        (
            f"Error {action} "
            f"{obj._meta.model_name}"  # noqa: SLF001
            f"[pk={obj.pk}]: {exc}"
        )
        for obj, exc in errors
    ]


def format_report(name: str, report: SyncModelReport) -> str:
    return (
        f"{name} (created={report.created}, "
        f"updated={report.updated}, deleted={report.deleted})"
    )


def format_errors(create_errors, update_errors, delete_errors) -> list[str]:
    return (
        make_error_messages(create_errors, "creating")
        + make_error_messages(update_errors, "updating")
        + make_error_messages(delete_errors, "deleting")
    )


def update_synced_models(
    posts_synced: Iterable[Post],
    posts_deleted: Iterable[Post],
    comments_synced: Iterable[Comment],
    comments_deleted: Iterable[Comment],
):
    if posts_synced:
        set_status_to_synced(Post, posts_synced)
    if comments_synced:
        set_status_to_synced(Comment, comments_synced)

    Comment.all_objects.filter(id__in=[obj.pk for obj in comments_deleted]).delete()
    Post.all_objects.filter(id__in=[obj.pk for obj in posts_deleted]).delete()


def sync_remote_data(
    client: httpx.Client, posts_url: str, comments_url: str
) -> SyncBlogReport:
    posts_sync = RemoteModelAPI(
        JSONAPIClient(client, posts_url), "Posts", RemotePostSerializer
    )
    comments_sync = RemoteModelAPI(
        JSONAPIClient(client, comments_url), "Comments", RemoteCommentSerializer
    )

    posts_created = SyncResult(*posts_sync.sync_created(Post.objects.created()))
    comments_created = SyncResult(
        *comments_sync.sync_created(Comment.objects.created())
    )
    posts_updated = SyncResult(*posts_sync.sync_updated(Post.objects.updated()))
    comments_updated = SyncResult(
        *comments_sync.sync_updated(Comment.objects.updated())
    )
    comments_deleted = SyncResult(
        *comments_sync.sync_deleted(Comment.objects.deleted())
    )
    posts_deleted = SyncResult(*posts_sync.sync_deleted(Post.objects.deleted()))

    update_synced_models(
        posts_created.instances + posts_updated.instances,
        posts_deleted.instances,
        comments_created.instances + comments_updated.instances,
        comments_deleted.instances,
    )

    return SyncBlogReport(
        SyncModelReport(
            len(posts_created.instances),
            len(posts_updated.instances),
            len(posts_deleted.instances),
            format_errors(
                posts_created.errors, posts_updated.errors, posts_deleted.errors
            ),
        ),
        SyncModelReport(
            len(comments_created.instances),
            len(comments_updated.instances),
            len(comments_deleted.instances),
            format_errors(
                comments_created.errors,
                comments_updated.errors,
                comments_deleted.errors,
            ),
        ),
    )


class Command(BaseCommand):
    help = "Syncs database posts and comments into the remote API"

    def add_arguments(self, parser):
        parser.add_argument(
            "--posts-url",
            action="store",
            default="https://jsonplaceholder.typicode.com/posts",
            type=str,
            help="Posts source",
        )
        parser.add_argument(
            "--comments-url",
            action="store",
            default="https://jsonplaceholder.typicode.com/comments",
            type=str,
            help="Comments source",
        )

    def handle(self, *args, **options):
        posts_url = options["posts_url"]
        comments_url = options["comments_url"]
        try:
            with httpx.Client() as client:
                report = sync_remote_data(client, posts_url, comments_url)
                self.process_report(report)
        except RemoteAPIError as exc:
            raise CommandError(str(exc)) from exc

    def process_report(self, blog_report: SyncBlogReport) -> None:
        if blog_report.success:
            msg = (
                "Successfully synced posts and comments.\n\t"
                + format_report("posts", blog_report.posts)
                + "\n\t"
                + format_report("comments", blog_report.comments)
            )
            self.stdout.write(self.style.SUCCESS(msg))
        else:
            for model in ("posts", "comments"):
                report = getattr(blog_report, model)
                if report.success:
                    msg = (
                        f"Successfully synced {model.capitalize()}.\n\t"
                        + format_report("posts", report)
                    )
                    self.stdout.write(self.style.SUCCESS(msg))
                elif report.partial_success:
                    msg = f"PARTIAL {model} SYNC"
                    self.stdout.write(self.style.SUCCESS(msg))
                    for error in report.errors:
                        self.stdout.write(self.style.WARNING(error))
                else:
                    msg = (
                        f"ERROR SYNCRONIZANDO {model} (num_errors={report.num_errors})"
                    )
                    self.stdout.write(self.style.ERROR(msg))
                    for error in report.errors:
                        self.stdout.write(self.style.ERROR(error))
