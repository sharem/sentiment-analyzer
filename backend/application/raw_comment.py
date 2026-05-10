"""RawComment — application-layer DTO for inbound comments."""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class RawComment:
    text: str
    subreddit: str
    post_id: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "RawComment":
        text = data.get("text")
        subreddit = data.get("subreddit")
        if not text:
            raise ValueError("missing_text_field")
        if not subreddit:
            raise ValueError("missing_subreddit_field")
        return cls(text=text, subreddit=subreddit, post_id=data.get("post_id"))
