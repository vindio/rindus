import pytest

from blog.sync_reports import SyncBlogReport
from blog.sync_reports import SyncModelReport


def test_sync_model_report_successs() -> None:
    report = SyncModelReport(0, 0, 0, [])
    assert report.success
    report.errors.append("err1")
    assert not report.success


@pytest.mark.parametrize(
    ("created", "updated", "deleted", "errors", "expected"),
    [
        (0, 0, 0, [], False),
        (0, 0, 0, ["err"], False),
        (1, 0, 0, [], True),
        (1, 0, 0, ["err"], True),
        (0, 1, 0, [], True),
        (0, 1, 0, ["err"], True),
        (0, 0, 1, [], True),
        (0, 0, 1, ["err"], True),
    ],
)
def test_sync_model_report_partial_success(
    created: int,
    updated: int,
    deleted: int,
    errors: list[str],
    expected: bool,  # noqa:FBT001
) -> None:
    report = SyncModelReport(created, updated, deleted, errors)
    assert report.partial_success == expected


def test_sync_model_num_items_synced() -> None:
    report = SyncModelReport(1, 2, 3, [])
    expected = 6
    assert report.num_items_synced == expected


@pytest.mark.parametrize(
    ("errors", "expected"),
    [
        ([], 0),
        (["err"], 1),
        (["err1", "err2"], 2),
    ],
)
def test_sync_model_report_num_errors(errors: list[str], expected: int) -> None:
    report = SyncModelReport(1, 1, 1, errors)
    assert report.num_errors == expected


@pytest.mark.parametrize(
    ("posts_errors", "comments_errors", "expected"),
    [
        ([], [], True),
        (["err"], [], False),
        ([], ["err1"], False),
        (["err1"], ["err2"], False),
    ],
)
def test_sync_blog_report_success(
    posts_errors: list[str],
    comments_errors: list[str],
    expected: bool,  # noqa:FBT001
) -> None:
    report = SyncBlogReport(
        SyncModelReport(0, 0, 0, posts_errors),
        SyncModelReport(0, 0, 0, comments_errors),
    )
    assert report.success == expected


@pytest.mark.parametrize(
    ("posts_report", "comments_report", "expected"),
    [
        (SyncModelReport(0, 0, 0, []), SyncModelReport(0, 0, 0, []), False),
        (SyncModelReport(1, 0, 0, []), SyncModelReport(0, 0, 0, []), True),
        (SyncModelReport(0, 0, 0, []), SyncModelReport(1, 0, 0, []), True),
        (SyncModelReport(1, 0, 0, []), SyncModelReport(1, 0, 0, []), True),
    ],
)
def test_sync_blog_report_partial_success(
    posts_report: SyncModelReport,
    comments_report: SyncModelReport,
    expected: bool,  # noqa:FBT001
) -> None:
    report = SyncBlogReport(posts_report, comments_report)
    assert report.partial_success == expected


def test_sync_blog_num_items_synced() -> None:
    report = SyncBlogReport(SyncModelReport(1, 2, 3, []), SyncModelReport(4, 5, 6, []))
    expected = 21
    assert report.num_items_synced == expected


@pytest.mark.parametrize(
    ("posts_errors", "comments_errors", "expected"),
    [
        ([], [], 0),
        (["err"], [], 1),
        ([], ["err"], 1),
        (["err"], ["err"], 2),
    ],
)
def test_sync_blog_report_num_errors(
    posts_errors: list[str], comments_errors: list[str], expected: int
) -> None:
    report = SyncBlogReport(
        SyncModelReport(1, 2, 3, posts_errors),
        SyncModelReport(4, 5, 6, comments_errors),
    )
    assert report.num_errors == expected
