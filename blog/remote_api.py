from collections.abc import Sequence

import httpx
from django.core.management.color import no_style
from django.db import connection
from django.db import transaction
from django.db.models import Model
from django.db.utils import Error
from rest_framework.serializers import BaseSerializer
from rest_framework.serializers import ValidationError

from blog.managers import SyncStatus
from blog.models import Comment
from blog.models import Post
from blog.serializers import RemoteCommentSerializer
from blog.serializers import RemotePostSerializer


class LoadRemoteDataError(Exception):
    pass


def _load_data(
    client: httpx.Client,
    url: str,
    model: type[Post | Comment],
    serializer: type[BaseSerializer[Post | Comment]],
) -> int:
    num_items = 0
    r = client.get(url)
    s = serializer(data=r.json(), many=True)
    try:
        if s.is_valid(raise_exception=True):
            objects = s.save(status=SyncStatus.SYNCED)
            num_items = len(objects)  # type: ignore[arg-type]
    except ValidationError as e:
        model_name = model._meta.verbose_name_plural  # noqa: SLF001
        msg = f"Error loading {model_name}: {s.errors!r}."
        raise LoadRemoteDataError(msg) from e
    return num_items


def load_posts(client: httpx.Client, url: str) -> int:
    return _load_data(client, url, Post, RemotePostSerializer)


def load_comments(client: httpx.Client, url: str) -> int:
    return _load_data(client, url, Comment, RemoteCommentSerializer)


def update_sequences(model_list: Sequence[type[Model]]):
    sequence_sql = connection.ops.sequence_reset_sql(no_style(), model_list)
    with connection.cursor() as cursor:
        for sql in sequence_sql:
            cursor.execute(sql)


def load_initial_data(posts_url: str, comments_url: str) -> tuple[int, int]:
    """
    Gets posts and comments from remote API and saves them to database.
    Posts and Comments status is set to SYNCED.

    Returns the number of imported posts and the number of imported comments.

    Raises LoadRemoteDataError in case of error.
    """
    num_posts = num_comments = 0
    headers = {
        "Content-type": "application/json; charset=UTF-8",
    }
    try:
        with transaction.atomic():
            with transaction.atomic(), httpx.Client(headers=headers) as client:
                num_posts = load_posts(client, posts_url)
                num_comments = load_comments(client, comments_url)
            update_sequences([Post, Comment])
    except httpx.RequestError as e:
        msg = f"An error occurred while requesting {e.request.url!r}.: {e}"
        raise LoadRemoteDataError(msg) from e
    except Error as e:
        msg = f"An error occurred saving data: {e}"
        raise LoadRemoteDataError(msg) from e
    return num_posts, num_comments
