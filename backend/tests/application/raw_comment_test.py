import pytest

from backend.application.raw_comment import RawComment


class TestFromDict:
    def test_parses_required_fields(self):
        raw = RawComment.from_dict({"text": "hello", "subreddit": "python"})

        assert raw == RawComment(text="hello", subreddit="python", post_id=None)

    def test_parses_optional_post_id(self):
        raw = RawComment.from_dict(
            {"text": "hello", "subreddit": "python", "post_id": "abc"}
        )

        assert raw.post_id == "abc"

    def test_raises_when_text_missing(self):
        with pytest.raises(ValueError, match="missing_text_field"):
            RawComment.from_dict({"subreddit": "python"})

    def test_raises_when_text_empty(self):
        with pytest.raises(ValueError, match="missing_text_field"):
            RawComment.from_dict({"text": "", "subreddit": "python"})

    def test_raises_when_subreddit_missing(self):
        with pytest.raises(ValueError, match="missing_subreddit_field"):
            RawComment.from_dict({"text": "hello"})

    def test_ignores_unknown_fields(self):
        raw = RawComment.from_dict(
            {"text": "hello", "subreddit": "python", "extra": "noise"}
        )

        assert raw == RawComment(text="hello", subreddit="python")


class TestToDict:
    def test_round_trips_through_from_dict(self):
        original = RawComment(text="hi", subreddit="python", post_id="abc")

        assert RawComment.from_dict(original.to_dict()) == original

    def test_includes_post_id_key_even_when_none(self):
        d = RawComment(text="hi", subreddit="python").to_dict()

        assert d == {"text": "hi", "subreddit": "python", "post_id": None}
