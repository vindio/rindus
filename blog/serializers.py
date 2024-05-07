from rest_framework import serializers

from blog.models import DEFAULT_USER_ID
from blog.models import Comment
from blog.models import Post


class PostSerializer(serializers.ModelSerializer[Post]):
    class Meta:
        model = Post
        fields = ["id", "user_id", "title", "body"]
        read_only_fields = ["id", "user_id"]

    def create(self, validated_data) -> Post:
        validated_data["user_id"] = DEFAULT_USER_ID
        return Post.objects.create(**validated_data)


class CommentSerializer(serializers.ModelSerializer[Comment]):
    class Meta:
        model = Comment
        fields = ["id", "post", "name", "email", "body"]
        read_only_fields = ["id"]


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
