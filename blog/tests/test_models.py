import pytest

from blog.models import Comment
from blog.models import Post
from blog.tests.factories import PostFactory


def test_post_str():
    title = "test title"
    post = Post(title=title, user_id=1, body="test body")
    assert str(post) == title


def test_comment_str():
    pk = 33
    name = "test name"
    post = Post(title="test title", user_id=1, body="test body")
    comment = Comment(
        id=pk, name=name, email="test@test.local", body="test body", post=post
    )
    assert str(comment) == f"Comment[id={pk}] by {name}"


# Using Post subclass to test SyncStatus Abstract Base Class


@pytest.mark.django_db()
def test_new_post_status_is_created():
    post = PostFactory()
    assert post.status == Post.SyncStatus.CREATED


@pytest.mark.parametrize(
    ("status"),
    [
        Post.SyncStatus.CREATED,
        Post.SyncStatus.SYNCED,
        Post.SyncStatus.UPDATED,
        Post.SyncStatus.DELETED,
    ],
)
@pytest.mark.django_db()
def test_new_post_status_is_created_ignoring__provided_status(status):
    post = PostFactory(status=status)
    assert post.status == Post.SyncStatus.CREATED


@pytest.mark.django_db()
def test_modified_post_status_is_updated():
    post = PostFactory()
    post.user_id = 123
    post.save()
    assert post.status == Post.SyncStatus.UPDATED


@pytest.mark.django_db()
def test_deleted_post_status_is_set_to_deleted():
    post = PostFactory()
    post.delete()
    assert post.status == Post.SyncStatus.DELETED
    assert Post.deleted.filter(id=post.pk, status=Post.SyncStatus.DELETED).exists()


@pytest.mark.parametrize(
    ("status", "expected_result"),
    [
        (Post.SyncStatus.CREATED, False),
        (Post.SyncStatus.SYNCED, False),
        (Post.SyncStatus.UPDATED, False),
        (Post.SyncStatus.DELETED, True),
    ],
)
def test_post_is_deleted_property(status, expected_result):
    post = Post(user_id=1, title="title", body="body", status=status)
    assert post.is_deleted == expected_result


@pytest.mark.parametrize(
    ("status", "expected_result"),
    [
        (Post.SyncStatus.CREATED, False),
        (Post.SyncStatus.SYNCED, True),
        (Post.SyncStatus.UPDATED, False),
        (Post.SyncStatus.DELETED, False),
    ],
)
def test_post_is_synced_property(status, expected_result):
    post = Post(user_id=1, title="title", body="body", status=status)
    assert post.is_synced == expected_result


@pytest.mark.parametrize(
    ("status"),
    [
        Post.SyncStatus.CREATED,
        Post.SyncStatus.SYNCED,
        Post.SyncStatus.UPDATED,
        Post.SyncStatus.DELETED,
    ],
)
@pytest.mark.django_db()
def test_sync_post(status):
    post = PostFactory()
    post.status = status
    post.save(update_fields=("status",))
    assert post.status == status
    post.sync()
    assert post.status == Post.SyncStatus.SYNCED
    assert Post.objects.filter(id=post.id, status=Post.SyncStatus.SYNCED)


@pytest.mark.parametrize(
    ("status", "expected_status"),
    [
        (Post.SyncStatus.CREATED, Post.SyncStatus.UPDATED),
        (Post.SyncStatus.SYNCED, Post.SyncStatus.UPDATED),
        (Post.SyncStatus.UPDATED, Post.SyncStatus.UPDATED),
        (Post.SyncStatus.DELETED, Post.SyncStatus.DELETED),
    ],
)
@pytest.mark.django_db()
def test_post_save(status, expected_status):
    post = PostFactory()
    Post.objects.update(status=status)
    post.refresh_from_db()
    post.save()
    assert post.status == expected_status


@pytest.mark.parametrize(
    ("status"),
    [
        Post.SyncStatus.CREATED,
        Post.SyncStatus.SYNCED,
        Post.SyncStatus.UPDATED,
        Post.SyncStatus.DELETED,
    ],
)
@pytest.mark.django_db()
def test_post_save_with_status_in_update_fields_sets_provided_status(status):
    post = PostFactory()
    Post.objects.update(status=status)
    post.refresh_from_db()
    post.status = status
    post.save(update_fields=("status",))
    assert post.status == status


@pytest.mark.django_db()
def test_post_save_with_status_not_in_update_fields_updates_status():
    post = PostFactory()
    assert post.status == Post.SyncStatus.CREATED
    post.title = "new title"
    post.save(update_fields=("title",))
    assert post.status == Post.SyncStatus.UPDATED
