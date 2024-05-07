import factory
from faker import Faker

from blog.models import DEFAULT_USER_ID
from blog.models import Comment
from blog.models import Post

fake = Faker()


class PostFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Post

    user_id = DEFAULT_USER_ID
    title = fake.text(max_nb_chars=20)
    body = fake.text()


class CommentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Comment

    post = factory.SubFactory(PostFactory)
    name = fake.name()
    email = fake.email()
    body = fake.text()
