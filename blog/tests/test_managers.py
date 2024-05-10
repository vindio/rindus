import pytest
from django.db import models

from blog.managers import DeletedManager
from blog.managers import SyncStatusManager
from blog.models import Post
from blog.tests.factories import PostFactory


@pytest.mark.parametrize(
    ("attribute", "cls"),
    [
        ("all_objects", models.Manager),
        ("objects", SyncStatusManager),
        ("deleted", DeletedManager),
    ],
)
def test_sync_status_managers(attribute, cls) -> None:
    manager = getattr(Post, attribute)
    assert isinstance(manager, cls)


@pytest.mark.django_db()
def test_sync_status_manager_created() -> None:
    num_status_created = 2
    posts = [
        *PostFactory.build_batch(num_status_created, status=Post.SyncStatus.CREATED),
        PostFactory.build(status=Post.SyncStatus.UPDATED),
        PostFactory.build(status=Post.SyncStatus.SYNCED),
        PostFactory.build(status=Post.SyncStatus.DELETED),
    ]
    Post.objects.bulk_create(posts)
    assert Post.objects.created().count() == num_status_created
    for post in Post.objects.created():
        assert post.status == Post.SyncStatus.CREATED


@pytest.mark.django_db()
def test_sync_status_manager_updated() -> None:
    num_status_updated = 2
    posts = [
        PostFactory.build(status=Post.SyncStatus.CREATED),
        *PostFactory.build_batch(num_status_updated, status=Post.SyncStatus.UPDATED),
        PostFactory.build(status=Post.SyncStatus.SYNCED),
        PostFactory.build(status=Post.SyncStatus.DELETED),
    ]
    Post.objects.bulk_create(posts)
    assert Post.objects.updated().count() == num_status_updated
    for post in Post.objects.updated():
        assert post.status == Post.SyncStatus.UPDATED


@pytest.mark.django_db()
def test_sync_status_manager_synced() -> None:
    num_status_synced = 2
    posts = [
        PostFactory.build(status=Post.SyncStatus.CREATED),
        PostFactory.build(status=Post.SyncStatus.UPDATED),
        *PostFactory.build_batch(num_status_synced, status=Post.SyncStatus.SYNCED),
        PostFactory.build(status=Post.SyncStatus.DELETED),
    ]
    Post.objects.bulk_create(posts)
    assert Post.objects.synced().count() == num_status_synced
    for post in Post.objects.synced():
        assert post.status == Post.SyncStatus.SYNCED


@pytest.mark.django_db()
def test_sync_status_manager_deleted() -> None:
    num_status_deleted = 2
    posts = [
        PostFactory.build(status=Post.SyncStatus.CREATED),
        PostFactory.build(status=Post.SyncStatus.UPDATED),
        PostFactory.build(status=Post.SyncStatus.SYNCED),
        *PostFactory.build_batch(num_status_deleted, status=Post.SyncStatus.DELETED),
    ]
    Post.objects.bulk_create(posts)
    assert Post.objects.deleted().count() == num_status_deleted
    for post in Post.objects.deleted():
        assert post.status == Post.SyncStatus.DELETED


@pytest.mark.django_db()
def test_sync_status_manager_delete() -> None:
    num_posts = 4
    posts = [
        PostFactory.build(status=Post.SyncStatus.CREATED),
        PostFactory.build(status=Post.SyncStatus.UPDATED),
        PostFactory.build(status=Post.SyncStatus.SYNCED),
        PostFactory.build(status=Post.SyncStatus.DELETED),
    ]
    assert len(posts) == num_posts
    Post.objects.bulk_create(posts)
    Post.objects.delete()
    num_expected_posts = 0
    assert Post.objects.count() == num_expected_posts
    assert Post.deleted.count() == num_posts


@pytest.mark.django_db()
def test_sync_status_manager_real_delete() -> None:
    num_posts = 5
    num_status_deleted = 2
    posts = [
        PostFactory.build(status=Post.SyncStatus.CREATED),
        PostFactory.build(status=Post.SyncStatus.UPDATED),
        PostFactory.build(status=Post.SyncStatus.SYNCED),
        *PostFactory.build_batch(num_status_deleted, status=Post.SyncStatus.DELETED),
    ]
    assert len(posts) == num_posts
    Post.objects.bulk_create(posts)
    Post.objects.real_delete()
    num_posts_expected = 0
    assert Post.objects.count() == num_posts_expected
    assert Post.all_objects.count() == num_status_deleted


@pytest.mark.django_db()
def test_deleted_manager_real_delete() -> None:
    num_posts = 4
    num_posts_expected = 3
    posts = [
        PostFactory.build(status=Post.SyncStatus.CREATED),
        PostFactory.build(status=Post.SyncStatus.UPDATED),
        PostFactory.build(status=Post.SyncStatus.SYNCED),
        PostFactory.build(status=Post.SyncStatus.DELETED),
    ]
    assert len(posts) == num_posts
    Post.objects.bulk_create(posts)
    Post.deleted.real_delete()
    num_posts_status_deleted_expected = 0
    assert Post.deleted.count() == num_posts_status_deleted_expected
    assert Post.all_objects.count() == num_posts_expected
