import pytest

from backend.domain.comment import Comment, Sentiment
from backend.infrastructure.nlp.textblob_analyzer import (
    NEGATIVE_THRESHOLD,
    POSITIVE_THRESHOLD,
    analyze_sentiment,
    classify_polarity,
)

TEXTBLOB_PATCH = "backend.infrastructure.nlp.textblob_analyzer.TextBlob"


class TestClassifyPolarity:
    def test_positive(self):
        assert classify_polarity(0.5) == Sentiment.POSITIVE

    def test_negative(self):
        assert classify_polarity(-0.5) == Sentiment.NEGATIVE

    def test_neutral_zero(self):
        assert classify_polarity(0.0) == Sentiment.NEUTRAL

    def test_exactly_at_positive_threshold_is_neutral(self):
        assert classify_polarity(POSITIVE_THRESHOLD) == Sentiment.NEUTRAL

    def test_exactly_at_negative_threshold_is_neutral(self):
        assert classify_polarity(NEGATIVE_THRESHOLD) == Sentiment.NEUTRAL

    def test_just_above_positive_threshold(self):
        assert classify_polarity(POSITIVE_THRESHOLD + 0.01) == Sentiment.POSITIVE

    def test_just_below_negative_threshold(self):
        assert classify_polarity(NEGATIVE_THRESHOLD - 0.01) == Sentiment.NEGATIVE

    @pytest.mark.parametrize("polarity,expected", [
        (1.0, Sentiment.POSITIVE),
        (-1.0, Sentiment.NEGATIVE),
        (0.0, Sentiment.NEUTRAL),
        (0.11, Sentiment.POSITIVE),
        (-0.11, Sentiment.NEGATIVE),
    ])
    def test_parametrized(self, polarity, expected):
        assert classify_polarity(polarity) == expected


class TestAnalyzeSentiment:
    def test_returns_comment(self):
        assert isinstance(analyze_sentiment("hello world"), Comment)

    def test_text_preserved(self):
        assert analyze_sentiment("test text").text == "test text"

    def test_sentiment_matches_polarity(self, mocker):
        mocker.patch(TEXTBLOB_PATCH).return_value.sentiment.polarity = 0.8
        comment = analyze_sentiment("anything")
        assert comment.sentiment == Sentiment.POSITIVE
        assert comment.polarity == 0.8

    def test_timestamp_is_set(self):
        assert analyze_sentiment("hello").timestamp is not None
