from django.db import models


class SyncStatus(models.TextChoices):
    SYNCED = "S", "Synced"
    CREATED = "C", "Created"
    UPDATED = "U", "Updated"
    DELETED = "D", "Deleted"


class SyncStatusQuerySet(models.QuerySet):
    def created(self) -> "SyncStatusQuerySet":
        return self.filter(status=SyncStatus.CREATED)

    def updated(self) -> "SyncStatusQuerySet":
        return self.filter(status=SyncStatus.UPDATED)

    def synced(self) -> "SyncStatusQuerySet":
        return self.filter(status=SyncStatus.SYNCED)

    def deleted(self) -> "SyncStatusQuerySet":
        return self.filter(status=SyncStatus.DELETED)

    def delete(self) -> tuple[int, dict[str, int]]:
        self.update(status=SyncStatus.DELETED)
        return 0, {}


class SyncStatusManager(models.Manager):
    def _get_queryset(self) -> "SyncStatusQuerySet":
        return SyncStatusQuerySet(self.model, using=self._db)

    def get_queryset(self) -> "SyncStatusQuerySet":
        return self._get_queryset().exclude(status=SyncStatus.DELETED)

    def created(self) -> "SyncStatusQuerySet":
        return self._get_queryset().created()

    def updated(self) -> "SyncStatusQuerySet":
        return self._get_queryset().updated()

    def synced(self) -> "SyncStatusQuerySet":
        return self._get_queryset().synced()

    def deleted(self) -> "SyncStatusQuerySet":
        return self._get_queryset().deleted()

    def real_delete(self) -> tuple[int, dict[str, int]]:
        return super().get_queryset().exclude(status=SyncStatus.DELETED).delete()

    def delete(self) -> tuple[int, dict[str, int]]:
        return self.get_queryset().delete()


class DeletedManager(models.Manager):
    def get_queryset(self) -> SyncStatusQuerySet:
        return SyncStatusQuerySet(self.model, using=self._db).filter(
            status=SyncStatus.DELETED
        )

    def real_delete(self) -> tuple[int, dict[str, int]]:
        return super().get_queryset().filter(status=SyncStatus.DELETED).delete()
