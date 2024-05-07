from django.db import models


class SyncStatus(models.TextChoices):
    SYNCED = "S", "Synced"
    CREATED = "C", "Created"
    UPDATED = "U", "Updated"
    DELETED = "D", "Deleted"


class SyncStatusQuerySet(models.QuerySet):
    def created(self):
        return self.filter(status=SyncStatus.CREATED)

    def updated(self):
        return self.filter(status=SyncStatus.UPDATED)

    def synced(self):
        return self.filter(status=SyncStatus.SYNCED)

    def deleted(self):
        return self.filter(status=SyncStatus.DELETED)

    def delete(self):
        self.update(status=SyncStatus.DELETED)
        return 0, {}


class SyncStatusManager(models.Manager):
    def _get_queryset(self):
        return SyncStatusQuerySet(self.model, using=self._db)

    def get_queryset(self):
        return self._get_queryset().exclude(status=SyncStatus.DELETED)

    def created(self):
        return self._get_queryset().created()

    def updated(self):
        return self._get_queryset().updated()

    def synced(self):
        return self._get_queryset().synced()

    def deleted(self):
        return self._get_queryset().deleted()

    def real_delete(self):
        return super().get_queryset().exclude(status=SyncStatus.DELETED).delete()

    def delete(self):
        return self.get_queryset().delete()


class DeletedManager(models.Manager):
    def get_queryset(self):
        return SyncStatusQuerySet(self.model, using=self._db).filter(
            status=SyncStatus.DELETED
        )

    def real_delete(self):
        return super().get_queryset().filter(status=SyncStatus.DELETED).delete()
