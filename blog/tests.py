from .models import Comment
from .models import Post


def test_post_str():
    title = "test title"
    post = Post(title=title, user_id=1, body="test body")
    assert str(post) == title


def test_comment_str():
    pk = 33
    name = "test name"
    post = Post(title="test title", user_id=1, body="test body")
    post = Comment(
        id=pk, name=name, email="test@test.local", body="test body", post=post
    )
    assert str(post) == f"Comment[id={pk}] by {name}"
