import pytest

from backend.infrastructure.repositories.sqlite_user_repository import (
    SQLiteUserRepository,
)


@pytest.fixture
def repo(tmp_path):
    return SQLiteUserRepository(db_path=str(tmp_path / "users.db"))


class TestUpsertFromGithub:
    def test_creates_user_when_github_id_is_new(self, repo):
        user = repo.upsert_from_github(
            github_id=42, github_login="octocat", avatar_url="https://x/a.png"
        )

        assert user.id is not None
        assert user.github_id == 42
        assert user.github_login == "octocat"
        assert user.avatar_url == "https://x/a.png"

    def test_returns_same_id_when_github_id_already_exists(self, repo):
        first = repo.upsert_from_github(42, "octocat", "https://x/a.png")

        second = repo.upsert_from_github(42, "octocat", "https://x/a.png")

        assert second.id == first.id

    def test_updates_login_and_avatar_on_existing_user(self, repo):
        repo.upsert_from_github(42, "old_login", "old_avatar")

        updated = repo.upsert_from_github(42, "new_login", "new_avatar")

        assert updated.github_login == "new_login"
        assert updated.avatar_url == "new_avatar"

    def test_different_github_ids_create_distinct_users(self, repo):
        u1 = repo.upsert_from_github(1, "a", "x")
        u2 = repo.upsert_from_github(2, "b", "y")

        assert u1.id != u2.id


class TestGetById:
    def test_returns_user_when_id_exists(self, repo):
        created = repo.upsert_from_github(42, "octocat", "https://x/a.png")

        fetched = repo.get_by_id(created.id)

        assert fetched is not None
        assert fetched.github_login == "octocat"

    def test_returns_none_when_id_missing(self, repo):
        assert repo.get_by_id(99999) is None


class TestPersistence:
    def test_user_survives_across_instances(self, tmp_path):
        db = str(tmp_path / "u.db")
        SQLiteUserRepository(db_path=db).upsert_from_github(42, "octocat", "x")

        repo2 = SQLiteUserRepository(db_path=db)
        fetched = repo2.get_by_id(1)

        assert fetched is not None
        assert fetched.github_login == "octocat"
