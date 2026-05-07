from datetime import datetime

import pytest

from backend.domain.comment import Comment, Sentiment
from backend.infrastructure.repositories.sqlite_repository import (
    SQLiteCommentRepository,
)


@pytest.fixture
def make_comment():
    def _make(text: str, sentiment: str, polarity: float) -> Comment:
        return Comment(
            text=text,
            sentiment=Sentiment(sentiment),
            polarity=polarity,
            timestamp=datetime.now().isoformat(),
        )
    return _make


@pytest.fixture
def service(tmp_path):
    s = SQLiteCommentRepository(
        max_comments=5, db_path=str(tmp_path / "test.db")
    )
    yield s
    s.clear_data()


@pytest.fixture
def service_with_data(service, make_comment):
    for text, sentiment, polarity in [
        ("Great post!", "positive", 0.8),
        ("This is terrible", "negative", -0.7),
        ("It's okay", "neutral", 0.1),
        ("Love it!", "positive", 0.9),
    ]:
        service.add_comment(make_comment(text, sentiment, polarity))
    return service
