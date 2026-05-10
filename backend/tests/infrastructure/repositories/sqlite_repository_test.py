"""Tests for SQLiteCommentRepository."""

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
            f"Comment {i}" for i in range(6, 1, -1)
        ]
        assert service.get_sentiment_counts()["positive"] == 5


class TestDataRetrieval:
    def test_get_recent_comments_with_limit(self, service_with_data):
        assert len(service_with_data.get_recent_comments()) == 4
        assert len(service_with_data.get_recent_comments(limit=2)) == 2



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



class TestClear:
    def test_clear_removes_all_comments(self, service, make_comment):
        service.add_comment(make_comment("a", "positive", 0.5))
        service.add_comment(make_comment("b", "negative", -0.5))
        assert len(service.get_recent_comments()) == 2

        service.clear()

        assert service.get_recent_comments() == []
        assert service.get_sentiment_counts() == {"positive": 0, "negative": 0, "neutral": 0}

    def test_clear_is_idempotent_on_empty_db(self, service):
        service.clear()
        service.clear()
        assert service.get_recent_comments() == []


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
        assert comments[0].polarity == -1.0
        assert comments[1].polarity == 1.0
