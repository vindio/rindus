from collections.abc import Sequence

import httpx
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.core.management.color import no_style
from django.db import Error
from django.db import connection
from django.db import models
from django.db import transaction
from rest_framework.serializers import BaseSerializer

from blog.models import Comment
from blog.models import Post
from blog.models import set_status_to_synced
from blog.remote_api import JSONAPIClient
from blog.remote_api import RemoteAPIError
from blog.remote_api import RemoteModelAPI
from blog.serializers import RemoteCommentSerializer
from blog.serializers import RemotePostSerializer


def update_sequences(model_list: Sequence[type[models.Model]]) -> None:
    sequence_sql = connection.ops.sequence_reset_sql(no_style(), model_list)
    with connection.cursor() as cursor:
        for sql in sequence_sql:
            cursor.execute(sql)


def load_model(
    client: httpx.Client,
    url: str,
    model_name: str,
    serializer: type[BaseSerializer[models.Model]],
) -> list[models.Model]:
    api_client = JSONAPIClient(client, url)
    loader = RemoteModelAPI(api_client, model_name, serializer)
    return loader.get_initial_data()


def load_initial_data(
    client: httpx.Client, posts_url: str, comments_url: str
) -> tuple[list[models.Model], list[models.Model]]:
    try:
        with transaction.atomic():
            posts = load_model(client, posts_url, "Posts", RemotePostSerializer)
            comments = load_model(
                client, comments_url, "Comments", RemoteCommentSerializer
            )
            update_sequences([Post, Comment])
            set_status_to_synced(Post, posts)  # type: ignore[arg-type]
            set_status_to_synced(Comment, comments)  # type: ignore[arg-type]
    except Error as exc:
        error_msg = f"An error occurred saving data: {exc}"
        raise RemoteAPIError(error_msg) from exc
    return posts, comments


class Command(BaseCommand):
    help = "Load posts and comments from the remote API into the database"

    def add_arguments(self, parser) -> None:
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

    def handle(self, *args, **options) -> None:
        posts_url = options["posts_url"]
        comments_url = options["comments_url"]
        try:
            with httpx.Client() as client:
                posts, comments = load_initial_data(client, posts_url, comments_url)
        except RemoteAPIError as e:
            raise CommandError(str(e)) from e
        num_posts = len(posts)
        num_comments = len(comments)
        msg = f"Successfully loaded {num_posts} posts and {num_comments} comments."
        self.stdout.write(self.style.SUCCESS(msg))
