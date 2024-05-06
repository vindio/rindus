from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from blog.remote_api import LoadRemoteDataError
from blog.remote_api import load_initial_data


class Command(BaseCommand):
    help = "Load posts and comments from the remote API into the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--posts-url",
            action="store",
            default="https://jsonplaceholder.typicode.com/posts",
            type=str,
            help="Posts source",
        )
        parser.add_argument(
            "--comments-url",
            action="store",
            default="https://jsonplaceholder.typicode.com/comments",
            type=str,
            help="Comments source",
        )

    def handle(self, *args, **options):
        posts_url = options["posts_url"]
        comments_url = options["comments_url"]
        try:
            num_posts, num_comments = load_initial_data(posts_url, comments_url)
        except LoadRemoteDataError as e:
            raise CommandError(str(e)) from e
        msg = f"Successfully loaded {num_posts} posts and {num_comments} comments."
        self.stdout.write(self.style.SUCCESS(msg))
