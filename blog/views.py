from rest_framework.filters import OrderingFilter
from rest_framework.filters import SearchFilter
from rest_framework.viewsets import ModelViewSet

from .models import Comment
from .models import Post
from .serializers import CommentSerializer
from .serializers import PostSerializer


class PostViewSet(ModelViewSet):
    serializer_class = PostSerializer
    queryset = Post.objects.order_by("-id")
    filter_backends = (OrderingFilter, SearchFilter)
    filterset_fields = ("user_id",)
    ordering_fields = ("id", "user_id", "title")
    ordering = ("id",)
    search_fields = ("title", "body")


class CommentViewSet(ModelViewSet):
    serializer_class = CommentSerializer
    queryset = Comment.objects.order_by("-id")
    filter_backends = (OrderingFilter, SearchFilter)
    ordering_fields = ("id", "post", "name")
    ordering = ("id", "post")
    search_fields = ("name", "email", "body")
