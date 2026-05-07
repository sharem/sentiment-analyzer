"""Tests for SQLiteCommentRepository."""

import time

from backend.domain.comment import Sentiment
from backend.infrastructure.repositories.sqlite_repository import (
    SQLiteCommentRepository,
)


class TestAddComments:
    def test_add_multiple_comments(self, service, make_comment):
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
    def test_circular_buffer_overflow(self, service, make_comment):
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

    def test_get_stats_empty(self, service):
        stats = service.get_stats()
        assert stats["total_comments"] == 0
        assert stats["oldest_comment_timestamp"] is None
        assert stats["newest_comment_timestamp"] is None

    def test_get_stats_with_data(self, service, make_comment):
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
    def test_data_persists_across_instances(self, tmp_path, make_comment):
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



class TestEdgeCases:
    def test_empty_string_comment(self, service, make_comment):
        service.add_comment(make_comment("", "neutral", 0.0))
        comments = service.get_recent_comments()
        assert len(comments) == 1
        assert comments[0].text == ""

    def test_extreme_polarity_values(self, service, make_comment):
        service.add_comment(make_comment("Extreme positive", "positive", 1.0))
        service.add_comment(make_comment("Extreme negative", "negative", -1.0))
        comments = service.get_recent_comments()
        assert len(comments) == 2
        assert comments[0].polarity == 1.0
        assert comments[1].polarity == -1.0
