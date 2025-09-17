"""
Pytest-based tests for SentimentDataService.
"""

import pytest
import tempfile
import os
import threading
import time
import sys
from unittest.mock import patch

# Import the module under test
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from data_service import SentimentDataService  # noqa: E402


@pytest.fixture
def temp_file():
    """Create a temporary file for testing."""
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    temp_file.close()
    yield temp_file.name
    # Cleanup
    if os.path.exists(temp_file.name):
        os.unlink(temp_file.name)


@pytest.fixture
def service(temp_file):
    """Create a SentimentDataService instance for testing."""
    return SentimentDataService(max_comments=5, storage_file=temp_file)


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
        """Test that the service initializes with empty data."""
        service = SentimentDataService()
        # Clear any existing data to ensure clean initialization
        service.clear_data()
        assert len(service._recent_comments) == 0
        expected_counts = {'positive': 0, 'negative': 0, 'neutral': 0}
        assert service._sentiment_counts == expected_counts

    def test_custom_initialization(self, temp_file):
        """Test service initialization with custom parameters."""
        service = SentimentDataService(max_comments=50, storage_file=temp_file)
        assert service._max_comments == 50
        assert service._storage_file == temp_file
        assert len(service._recent_comments) == 0


class TestAddComments:
    """Test comment addition functionality."""

    def test_add_single_comment(self, service):
        """Test adding a single comment."""
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
        """Test adding multiple comments with different sentiments."""
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

    @pytest.mark.unit
    def test_add_comment_with_invalid_sentiment(self, service):
        """Test adding comment with invalid sentiment."""
        service.add_comment("Test", "invalid_sentiment", 0.0)

        # Should not affect valid sentiment counts
        counts = service.get_sentiment_counts()
        assert counts["positive"] == 0
        assert counts["negative"] == 0
        assert counts["neutral"] == 0


class TestCircularBuffer:
    """Test circular buffer behavior."""

    def test_circular_buffer_overflow(self, service):
        """Test that circular buffer works correctly when at capacity."""
        # Fill the buffer (max_comments=5) and add more
        for i in range(7):
            service.add_comment(f"Comment {i}", "positive", 0.5)

        comments = service.get_recent_comments()
        assert len(comments) == 5

        # Check that we have the latest comments (2, 3, 4, 5, 6)
        comment_texts = [c["text"] for c in comments]
        expected_texts = [f"Comment {i}" for i in range(2, 7)]
        assert comment_texts == expected_texts

        counts = service.get_sentiment_counts()
        assert counts["positive"] == 5

    def test_sentiment_count_accuracy_with_overflow(self, service):
        """Test that sentiment counts remain accurate with circular buffer."""
        # Add different sentiments to fill buffer
        sentiments = ["positive", "negative", "neutral",
                      "positive", "negative"]
        for i, sentiment in enumerate(sentiments):
            service.add_comment(f"Comment {i}", sentiment, 0.0)

        initial_counts = service.get_sentiment_counts()
        assert initial_counts["positive"] == 2
        assert initial_counts["negative"] == 2
        assert initial_counts["neutral"] == 1

        # Add one more positive (should remove the first positive)
        service.add_comment("New comment", "positive", 0.0)

        final_counts = service.get_sentiment_counts()
        assert final_counts["positive"] == 2  # Still 2
        assert final_counts["negative"] == 2  # Still 2
        assert final_counts["neutral"] == 1   # Still 1


class TestDataRetrieval:
    """Test data retrieval methods."""

    def test_get_recent_comments_with_limit(self, service_with_data):
        """Test getting recent comments with a limit."""
        all_comments = service_with_data.get_recent_comments()
        assert len(all_comments) == 4

        limited_comments = service_with_data.get_recent_comments(limit=2)
        assert len(limited_comments) == 2

        # Should get the most recent 2
        expected_texts = ["It's okay", "Love it!"]
        actual_texts = [c["text"] for c in limited_comments]
        assert actual_texts == expected_texts

    def test_get_sentiment_counts(self, service_with_data):
        """Test getting sentiment counts."""
        counts = service_with_data.get_sentiment_counts()
        assert counts["positive"] == 2
        assert counts["negative"] == 1
        assert counts["neutral"] == 1

    def test_get_stats_empty(self, service):
        """Test getting statistics with empty data."""
        stats = service.get_stats()
        assert stats["total_comments"] == 0
        assert stats["oldest_comment_timestamp"] is None
        assert stats["newest_comment_timestamp"] is None

    def test_get_stats_with_data(self, service):
        """Test getting statistics with data."""
        service.add_comment("First comment", "positive", 0.5)
        time.sleep(0.001)  # Small delay for different timestamps
        service.add_comment("Second comment", "negative", -0.3)

        stats = service.get_stats()
        assert stats["total_comments"] == 2
        assert stats["oldest_comment_timestamp"] is not None
        assert stats["newest_comment_timestamp"] is not None
        old_ts = stats["oldest_comment_timestamp"]
        new_ts = stats["newest_comment_timestamp"]
        assert old_ts != new_ts


class TestDataManagement:
    """Test data management operations."""

    def test_clear_data(self, service_with_data):
        """Test clearing all data."""
        # Verify data exists
        assert len(service_with_data.get_recent_comments()) == 4

        # Clear data
        service_with_data.clear_data()

        # Check everything is cleared
        assert len(service_with_data.get_recent_comments()) == 0
        counts = service_with_data.get_sentiment_counts()
        assert counts["positive"] == 0
        assert counts["negative"] == 0
        assert counts["neutral"] == 0


@pytest.mark.persistence
class TestPersistence:
    """Test persistence functionality."""

    def test_save_and_load_data(self, temp_file):
        """Test that data is properly saved to and loaded from file."""
        # Add data with first service instance
        service1 = SentimentDataService(max_comments=5, storage_file=temp_file)
        service1.add_comment("Persistent comment", "positive", 0.7)

        # Create new service instance with same file
        service2 = SentimentDataService(max_comments=5, storage_file=temp_file)

        # Check that data was loaded
        comments = service2.get_recent_comments()
        assert len(comments) == 1
        assert comments[0]["text"] == "Persistent comment"
        assert comments[0]["sentiment"] == "positive"

        counts = service2.get_sentiment_counts()
        assert counts["positive"] == 1

    def test_corrupted_file_handling(self, temp_file):
        """Test handling of corrupted JSON file."""
        # Write invalid JSON to the file
        with open(temp_file, 'w') as f:
            f.write("invalid json content")

        # Should handle gracefully and start fresh
        service = SentimentDataService(storage_file=temp_file)
        assert len(service.get_recent_comments()) == 0

    def test_missing_file_handling(self):
        """Test handling of missing storage file."""
        non_existent_path = "/tmp/non_existent_file_12345.json"
        service = SentimentDataService(storage_file=non_existent_path)

        # Should start with empty data
        assert len(service.get_recent_comments()) == 0

    @patch('builtins.open', side_effect=PermissionError("Permission denied"))
    def test_permission_error_handling(self, mock_open, service):
        """Test handling of permission errors during save."""
        # Should handle gracefully and not crash
        service.add_comment("Test comment", "positive", 0.5)
        # If we reach here, the exception was handled gracefully


@pytest.mark.threading
class TestThreadSafety:
    """Test thread safety."""

    def test_concurrent_access(self, service):
        """Test thread safety of the service."""
        num_threads = 10
        comments_per_thread = 5

        def add_comments(thread_id):
            """Add comments from a specific thread."""
            for i in range(comments_per_thread):
                service.add_comment(
                    f"Thread {thread_id} Comment {i}",
                    "positive",
                    0.5
                )

        # Start multiple threads
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=add_comments, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check final state
        comments = service.get_recent_comments()
        # Should have max_comments (5) due to circular buffer
        assert len(comments) == 5

        counts = service.get_sentiment_counts()
        assert counts["positive"] == 5


@pytest.mark.unit
class TestEdgeCases:
    """Test various edge cases."""

    def test_empty_string_comment(self, service):
        """Test adding comment with empty string."""
        service.add_comment("", "neutral", 0.0)
        comments = service.get_recent_comments()
        assert len(comments) == 1
        assert comments[0]["text"] == ""

    def test_very_long_comment(self, service):
        """Test adding very long comment."""
        long_text = "A" * 1000
        service.add_comment(long_text, "positive", 0.5)
        comments = service.get_recent_comments()
        assert len(comments) == 1
        assert comments[0]["text"] == long_text

    def test_extreme_polarity_values(self, service):
        """Test with extreme polarity values."""
        service.add_comment("Extreme positive", "positive", 1.0)
        service.add_comment("Extreme negative", "negative", -1.0)
        comments = service.get_recent_comments()
        assert len(comments) == 2
        assert comments[0]["polarity"] == 1.0
        assert comments[1]["polarity"] == -1.0


@pytest.mark.integration
class TestIntegration:
    """Integration tests for real-world scenarios."""

    def test_real_world_scenario(self, temp_file):
        """Test a realistic usage scenario."""
        # Simulate producer adding data
        producer_service = SentimentDataService(
            max_comments=10,
            storage_file=temp_file
        )

        # Add realistic comments
        realistic_comments = [
            ("I love this product!", "positive", 0.8),
            ("This is the worst thing ever", "negative", -0.9),
            ("It's okay, nothing special", "neutral", 0.1),
            ("Amazing experience!", "positive", 0.9),
            ("Could be better", "negative", -0.2),
        ]

        for text, sentiment, polarity in realistic_comments:
            producer_service.add_comment(text, sentiment, polarity)

        # Simulate consumer reading data
        consumer_service = SentimentDataService(storage_file=temp_file)

        # Verify data consistency
        comments = consumer_service.get_recent_comments()
        assert len(comments) == 5

        counts = consumer_service.get_sentiment_counts()
        assert counts["positive"] == 2
        assert counts["negative"] == 2
        assert counts["neutral"] == 1

        # Verify stats
        stats = consumer_service.get_stats()
        assert stats["total_comments"] == 5
        assert stats["oldest_comment_timestamp"] is not None
        assert stats["newest_comment_timestamp"] is not None
