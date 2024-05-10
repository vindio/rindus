class SyncModelReport:
    def __init__(self, created: int, updated: int, deleted: int, errors: list[str]):
        self.created = created
        self.updated = updated
        self.deleted = deleted
        self.errors = errors

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    @property
    def partial_success(self) -> bool:
        return self.num_items_synced > 0

    @property
    def num_items_synced(self) -> int:
        return self.created + self.updated + self.deleted

    @property
    def num_errors(self) -> int:
        return len(self.errors)


class SyncBlogReport:
    def __init__(self, posts_report: SyncModelReport, comments_report: SyncModelReport):
        self.posts = posts_report
        self.comments = comments_report

    @property
    def success(self) -> bool:
        return self.posts.success and self.comments.success

    @property
    def partial_success(self) -> bool:
        return self.posts.partial_success or self.comments.partial_success

    @property
    def num_items_synced(self) -> int:
        return self.posts.num_items_synced + self.comments.num_items_synced

    @property
    def num_errors(self) -> int:
        return self.posts.num_errors + self.comments.num_errors
