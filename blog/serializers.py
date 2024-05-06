from rest_framework import serializers

from blog.models import Comment
from blog.models import Post

DEFAULT_USER_ID = 99999942


class RemotePostListSerializer(serializers.ListSerializer):
    def create(self, validated_data):
        books = [Post(**item) for item in validated_data]
        return Post.objects.bulk_create(books)


class RemotePostSerializer(serializers.ModelSerializer[Post]):
    id = serializers.IntegerField()
    userId = serializers.IntegerField(  # noqa: N815
        source="user_id",
    )

    class Meta:
        model = Post
        list_serializer_class = RemotePostListSerializer
        fields = ["id", "userId", "title", "body"]


class RemoteCommentListSerializer(serializers.ListSerializer):
    def create(self, validated_data):
        comments = [Comment(**item) for item in validated_data]
        return Comment.objects.bulk_create(comments)


class RemoteCommentSerializer(serializers.ModelSerializer[Comment]):
    id = serializers.IntegerField()
    postId = serializers.IntegerField(source="post_id")  # noqa: N815

    class Meta:
        model = Comment
        list_serializer_class = RemoteCommentListSerializer
        fields = ["id", "postId", "name", "email", "body"]
