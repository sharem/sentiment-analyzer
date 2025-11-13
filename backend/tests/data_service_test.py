"""
Pytest-based tests for SentimentDataService.
"""

import os
import sys
import tempfile
import threading
import time

import pytest

# Import the module under test
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from data_service import SentimentDataService  # noqa: E402


@pytest.fixture
def temp_file():
    """Create a temporary file for testing."""
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    temp_file.close()
    yield temp_file.name
    if os.path.exists(temp_file.name):
        os.unlink(temp_file.name)


@pytest.fixture
def service(temp_file):
    """Create a SentimentDataService instance for testing."""
    service = SentimentDataService(max_comments=5, storage_file=temp_file)
    yield service
    service.clear_data()


@pytest.fixture
def service_with_data(service):
    """Create a service with some test data."""
    test_data = [
        ("Great post!", "positive", 0.8),
        ("This is terrible", "negative", -0.7),
        ("It's okay", "neutral", 0.1),
        ("Love it!", "positive", 0.9),
    ]

    for text, sentiment, polarity in test_data:
        service.add_comment(text, sentiment, polarity)

    return service


class TestInitialization:
    """Test service initialization."""

    def test_default_initialization(self):
        service = SentimentDataService()
        assert len(service.get_recent_comments()) == 0
        assert service.get_sentiment_counts() == {
            'positive': 0, 'negative': 0, 'neutral': 0
        }

    def test_custom_initialization(self, temp_file):
        service = SentimentDataService(
            max_comments=50,
            storage_file=temp_file
        )
        assert service._max_comments == 50
        assert len(service.get_recent_comments()) == 0


class TestAddComments:
    """Test comment addition functionality."""

    def test_add_single_comment(self, service):
        service.add_comment("Great post!", "positive", 0.8)

        comments = service.get_recent_comments()
        assert len(comments) == 1
        assert comments[0]["text"] == "Great post!"
        assert comments[0]["sentiment"] == "positive"
        assert comments[0]["polarity"] == 0.8
        assert "timestamp" in comments[0]

        counts = service.get_sentiment_counts()
        assert counts["positive"] == 1
        assert counts["negative"] == 0
        assert counts["neutral"] == 0

    def test_add_multiple_comments(self, service):
        comments_data = [
            ("Great post!", "positive", 0.8),
            ("This is terrible", "negative", -0.7),
            ("It's okay", "neutral", 0.1),
            ("Love it!", "positive", 0.9),
        ]

        for text, sentiment, polarity in comments_data:
            service.add_comment(text, sentiment, polarity)

        comments = service.get_recent_comments()
        assert len(comments) == 4

        counts = service.get_sentiment_counts()
        assert counts["positive"] == 2
        assert counts["negative"] == 1
        assert counts["neutral"] == 1


class TestCircularBuffer:
    """Test circular buffer behavior."""

    def test_circular_buffer_overflow(self, service):
        for i in range(7):
            service.add_comment(f"Comment {i}", "positive", 0.5)

        comments = service.get_recent_comments()
        assert len(comments) == 5

        comment_texts = [c["text"] for c in comments]
        expected_texts = [f"Comment {i}" for i in range(2, 7)]
        assert comment_texts == expected_texts

        counts = service.get_sentiment_counts()
        assert counts["positive"] == 5


class TestDataRetrieval:
    """Test data retrieval methods."""

    def test_get_recent_comments_with_limit(self, service_with_data):
        all_comments = service_with_data.get_recent_comments()
        assert len(all_comments) == 4

        limited_comments = service_with_data.get_recent_comments(limit=2)
        assert len(limited_comments) == 2

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
        service.add_comment("First comment", "positive", 0.5)
        time.sleep(0.001)
        service.add_comment("Second comment", "negative", -0.3)

        stats = service.get_stats()
        assert stats["total_comments"] == 2
        assert stats["oldest_comment_timestamp"] is not None
        assert stats["newest_comment_timestamp"] is not None


class TestDataManagement:
    """Test data management operations."""

    def test_clear_data(self, service_with_data):
        assert len(service_with_data.get_recent_comments()) == 4

        service_with_data.clear_data()

        assert len(service_with_data.get_recent_comments()) == 0
        counts = service_with_data.get_sentiment_counts()
        assert counts["positive"] == 0
        assert counts["negative"] == 0
        assert counts["neutral"] == 0


class TestPersistence:
    """Test persistence functionality."""

    def test_save_and_load_data(self, temp_file):
        service1 = SentimentDataService(
            max_comments=5,
            storage_file=temp_file
        )
        service1.add_comment("Persistent comment", "positive", 0.7)

        service2 = SentimentDataService(
            max_comments=5,
            storage_file=temp_file
        )

        comments = service2.get_recent_comments()
        assert len(comments) == 1
        assert comments[0]["text"] == "Persistent comment"
        assert comments[0]["sentiment"] == "positive"

        counts = service2.get_sentiment_counts()
        assert counts["positive"] == 1

    def test_corrupted_file_handling(self, temp_file):
        with open(temp_file, 'w') as f:
            f.write("invalid json content")

        service = SentimentDataService(storage_file=temp_file)
        assert len(service.get_recent_comments()) == 0


class TestThreadSafety:
    """Test thread safety."""

    def test_concurrent_access(self, service):
        num_threads = 10
        comments_per_thread = 5

        def add_comments(thread_id):
            for i in range(comments_per_thread):
                service.add_comment(
                    f"Thread {thread_id} Comment {i}",
                    "positive",
                    0.5
                )

        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=add_comments, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        comments = service.get_recent_comments()
        assert len(comments) == 5

        counts = service.get_sentiment_counts()
        assert counts["positive"] == 5


class TestEdgeCases:
    """Test various edge cases."""

    def test_empty_string_comment(self, service):
        service.add_comment("", "neutral", 0.0)
        comments = service.get_recent_comments()
        assert len(comments) == 1
        assert comments[0]["text"] == ""

    def test_extreme_polarity_values(self, service):
        service.add_comment("Extreme positive", "positive", 1.0)
        service.add_comment("Extreme negative", "negative", -1.0)
        comments = service.get_recent_comments()
        assert len(comments) == 2
        assert comments[0]["polarity"] == 1.0
        assert comments[1]["polarity"] == -1.0
