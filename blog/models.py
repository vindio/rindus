from collections.abc import Iterable

from django.db import models
from django.db import transaction

from blog.managers import DeletedManager
from blog.managers import SyncStatus
from blog.managers import SyncStatusManager

DEFAULT_USER_ID = 99999942


def set_status_to_synced(
    model: type["SyncStatusMixin"], objects: Iterable["SyncStatusMixin"]
) -> None:
    for obj in objects:
        obj.status = model.SyncStatus.SYNCED
    model.objects.bulk_update(objects, ["status"])


class SyncStatusMixin(models.Model):
    SyncStatus = SyncStatus

    status = models.CharField(
        max_length=1,
        choices=SyncStatus.choices,
        default=SyncStatus.CREATED,
    )

    objects: SyncStatusManager = SyncStatusManager()
    deleted: DeletedManager = DeletedManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True
        indexes = (models.Index(fields=["status"], name="%(class)s_sync_status_idx"),)

    def save(
        self,
        force_insert=False,  # noqa: FBT002
        force_update=False,  # noqa: FBT002
        using=None,
        update_fields=None,
    ) -> None:
        """
        Saves object instance updating SyncStatus

        To force saving provided self.status whitout modification "status" must be
        included in `update_fields` and self.pk must be not None.

        self.status is set to CREATED if pk is None
        sel.status is set to UPDATED if pk is not None and current self.status
        is not DELETED.
        """
        status_in_update_fields = update_fields and "status" in update_fields
        if update_fields and "status" not in update_fields:
            update_fields = (*update_fields, "status")

        if self.pk is None:
            self.status = SyncStatus.CREATED
        elif not status_in_update_fields and self.status != SyncStatus.DELETED:
            self.status = SyncStatus.UPDATED
        super().save(
            using=using,
            force_insert=force_insert,
            force_update=force_update,
            update_fields=update_fields,
        )

    def delete(self, using=None, keep_parents=False):  # noqa: FBT002
        self.status = SyncStatus.DELETED
        self.save(update_fields=("status",))
        return 0, {}

    @property
    def is_deleted(self) -> bool:
        return self.status == SyncStatus.DELETED

    @property
    def is_synced(self) -> bool:
        return self.status == SyncStatus.SYNCED

    def sync(self) -> None:
        self.status = SyncStatus.SYNCED
        self.save(update_fields=("status",))


class Post(SyncStatusMixin):
    user_id = models.PositiveIntegerField()
    title = models.CharField(max_length=255)
    body = models.TextField()

    def __str__(self) -> str:
        return self.title

    def delete(self, using=None, keep_parents=False) -> tuple[int, dict[str, int]]:  # noqa: FBT002
        with transaction.atomic():
            self.comments.update(status=SyncStatus.DELETED)
            self.status = SyncStatus.DELETED
            self.save(update_fields=("status",))
        return 0, {}


class Comment(SyncStatusMixin):
    post = models.ForeignKey(
        Post,
        related_name="comments",
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=100)
    email = models.EmailField()
    body = models.TextField()

    def __str__(self) -> str:
        return f"Comment[id={self.pk}] by {self.name}"
