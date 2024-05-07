from django.conf import settings
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from blog.views import CommentViewSet
from blog.views import PostViewSet

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("posts", PostViewSet)
router.register("comments", CommentViewSet)


app_name = "api"

urlpatterns = router.urls
