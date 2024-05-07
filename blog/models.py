from django.db import models

DEFAULT_USER_ID = 99999942


class Post(models.Model):
    user_id = models.PositiveIntegerField()
    title = models.CharField(max_length=255)
    body = models.TextField()

    def __str__(self) -> str:
        return self.title


class Comment(models.Model):
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
