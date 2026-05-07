"""Tests for SQLiteCommentRepository."""

import threading
import time
from datetime import datetime

import pytest

from backend.domain.comment import Comment, Sentiment
from backend.infrastructure.repositories.sqlite_repository import (
    SQLiteCommentRepository,
)


def make_comment(
    text: str, sentiment: str, polarity: float
) -> Comment:
    return Comment(
        text=text,
        sentiment=Sentiment(sentiment),
        polarity=polarity,
        timestamp=datetime.now().isoformat(),
    )


@pytest.fixture
def service(tmp_path):
    """SQLiteCommentRepository backed by a temp file."""
    s = SQLiteCommentRepository(
        max_comments=5, db_path=str(tmp_path / "test.db")
    )
    yield s
    s.clear_data()


@pytest.fixture
def service_with_data(service):
    test_data = [
        ("Great post!", "positive", 0.8),
        ("This is terrible", "negative", -0.7),
        ("It's okay", "neutral", 0.1),
        ("Love it!", "positive", 0.9),
    ]
    for text, sentiment, polarity in test_data:
        service.add_comment(make_comment(text, sentiment, polarity))
    return service


class TestInitialization:
    def test_default_initialization(self, tmp_path):
        db = str(tmp_path / "test.db")
        service = SQLiteCommentRepository(db_path=db)
        assert len(service.get_recent_comments()) == 0
        assert service.get_sentiment_counts() == {
            "positive": 0,
            "negative": 0,
            "neutral": 0,
        }

    def test_custom_initialization(self, tmp_path):
        db = str(tmp_path / "test.db")
        service = SQLiteCommentRepository(max_comments=50, db_path=db)
        assert service._max_comments == 50
        assert len(service.get_recent_comments()) == 0


class TestAddComments:
    def test_add_single_comment(self, service):
        service.add_comment(make_comment("Great post!", "positive", 0.8))

        comments = service.get_recent_comments()
        assert len(comments) == 1
        assert comments[0].text == "Great post!"
        assert comments[0].sentiment == Sentiment.POSITIVE
        assert comments[0].polarity == 0.8
        assert comments[0].timestamp is not None

        counts = service.get_sentiment_counts()
        assert counts["positive"] == 1
        assert counts["negative"] == 0
        assert counts["neutral"] == 0

    def test_add_multiple_comments(self, service):
        for text, sentiment, polarity in [
            ("Great post!", "positive", 0.8),
            ("This is terrible", "negative", -0.7),
            ("It's okay", "neutral", 0.1),
            ("Love it!", "positive", 0.9),
        ]:
            service.add_comment(make_comment(text, sentiment, polarity))

        assert len(service.get_recent_comments()) == 4
        counts = service.get_sentiment_counts()
        assert counts["positive"] == 2
        assert counts["negative"] == 1
        assert counts["neutral"] == 1


class TestCircularBuffer:
    def test_circular_buffer_overflow(self, service):
        for i in range(7):
            service.add_comment(
                make_comment(f"Comment {i}", "positive", 0.5)
            )

        comments = service.get_recent_comments()
        assert len(comments) == 5
        assert [c.text for c in comments] == [
            f"Comment {i}" for i in range(2, 7)
        ]
        assert service.get_sentiment_counts()["positive"] == 5


class TestDataRetrieval:
    def test_get_recent_comments_with_limit(self, service_with_data):
        assert len(service_with_data.get_recent_comments()) == 4
        assert len(service_with_data.get_recent_comments(limit=2)) == 2

    def test_get_sentiment_counts(self, service_with_data):
        counts = service_with_data.get_sentiment_counts()
        assert counts["positive"] == 2
        assert counts["negative"] == 1
        assert counts["neutral"] == 1

    def test_get_stats_empty(self, service):
        stats = service.get_stats()
        assert stats["total_comments"] == 0
        assert stats["oldest_comment_timestamp"] is None
        assert stats["newest_comment_timestamp"] is None

    def test_get_stats_with_data(self, service):
        service.add_comment(make_comment("First", "positive", 0.5))
        time.sleep(0.001)
        service.add_comment(make_comment("Second", "negative", -0.3))

        stats = service.get_stats()
        assert stats["total_comments"] == 2
        assert stats["oldest_comment_timestamp"] is not None
        assert stats["newest_comment_timestamp"] is not None


class TestDataManagement:
    def test_clear_data(self, service_with_data):
        assert len(service_with_data.get_recent_comments()) == 4
        service_with_data.clear_data()
        assert len(service_with_data.get_recent_comments()) == 0
        counts = service_with_data.get_sentiment_counts()
        assert counts["positive"] == 0
        assert counts["negative"] == 0
        assert counts["neutral"] == 0


class TestPersistence:
    def test_data_persists_across_instances(self, tmp_path):
        db = str(tmp_path / "persistent.db")
        service1 = SQLiteCommentRepository(max_comments=5, db_path=db)
        service1.add_comment(
            make_comment("Persistent comment", "positive", 0.7)
        )

        service2 = SQLiteCommentRepository(max_comments=5, db_path=db)
        comments = service2.get_recent_comments()
        assert len(comments) == 1
        assert comments[0].text == "Persistent comment"
        assert comments[0].sentiment == Sentiment.POSITIVE
        assert service2.get_sentiment_counts()["positive"] == 1


class TestThreadSafety:
    def test_concurrent_access(self, tmp_path):
        db = str(tmp_path / "thread_test.db")
        service = SQLiteCommentRepository(max_comments=1000, db_path=db)
        num_threads = 10
        comments_per_thread = 5

        def add_comments(thread_id):
            sentiment = "positive" if thread_id % 2 == 0 else "negative"
            for i in range(comments_per_thread):
                service.add_comment(
                    make_comment(
                        f"Thread {thread_id} Comment {i}", sentiment, 0.5
                    )
                )

        threads = [
            threading.Thread(target=add_comments, args=(i,))
            for i in range(num_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(service.get_recent_comments()) == 50
        counts = service.get_sentiment_counts()
        assert counts["positive"] == 25
        assert counts["negative"] == 25


class TestEdgeCases:
    def test_empty_string_comment(self, service):
        service.add_comment(make_comment("", "neutral", 0.0))
        comments = service.get_recent_comments()
        assert len(comments) == 1
        assert comments[0].text == ""

    def test_extreme_polarity_values(self, service):
        service.add_comment(
            make_comment("Extreme positive", "positive", 1.0)
        )
        service.add_comment(
            make_comment("Extreme negative", "negative", -1.0)
        )
        comments = service.get_recent_comments()
        assert len(comments) == 2
        assert comments[0].polarity == 1.0
        assert comments[1].polarity == -1.0
